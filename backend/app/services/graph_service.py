"""
Neo4j investigation graph service.

Graph schema:

    (:Actor)
    (:Handle)
    (:Wallet)
    (:Marketplace)
    (:Infrastructure)
    (:Observation)
    (:PGPKey)

Relationships:

    Actor -[:USES_HANDLE]-> Handle
    Handle -[:USED_WALLET]-> Wallet
    Handle -[:USES_MARKETPLACE]-> Marketplace
    Handle -[:HAS_PGP_KEY]-> PGPKey
    Handle -[:TRUSTS]-> Handle
    PGPKey -[:TRUSTS]-> Handle
    Actor -[:HAS_INFRASTRUCTURE]-> Infrastructure
    Actor -[:HAS_OBSERVATION]-> Observation
    Handle -[:HAS_OBSERVATION]-> Observation
    Observation -[:EVIDENCE_OF]-> Infrastructure

The graph is intentionally evidence-oriented. It does not claim that
two handles belong to the same person simply because they are connected.
Instead, it exposes reusable infrastructure, wallets, observations,
and other signals for investigator review.
"""

from typing import Any, Dict, List, Optional

from app.database.neo4j_client import neo4j_conn


def sync_actor_batch(
    actors: List[Dict[str, Any]],
    handles: List[Dict[str, Any]],
    wallets: List[Dict[str, Any]],
) -> None:
    """
    Bulk-upsert the core Actor/Handle/Wallet graph.

    Kept compatible with the existing ingestion pipeline.
    """

    if actors:
        neo4j_conn.write(
            """
            UNWIND $rows AS row
            MERGE (a:Actor {actor_id: row.actor_id})
            SET a.primary_handle = row.primary_handle,
                a.risk_category = row.risk_category,
                a.confidence_score = row.confidence_score
            """,
            {"rows": actors},
        )

    if handles:
        handle_rows = [
            h
            for h in handles
            if h.get("handle_id") and h.get("handle") and h.get("actor_id")
        ]

        if handle_rows:
            neo4j_conn.write(
                """
                UNWIND $rows AS row

                MERGE (h:Handle {handle_id: row.handle_id})
                SET h.handle = row.handle,
                    h.platform = row.platform,
                    h.status = row.status

                WITH h, row

                MATCH (a:Actor {actor_id: row.actor_id})
                MERGE (a)-[:USES_HANDLE]->(h)

                FOREACH (
                    platform IN CASE
                        WHEN row.platform IS NULL OR row.platform = ""
                        THEN []
                        ELSE [row.platform]
                    END |
                    MERGE (m:Marketplace {name: platform})
                    MERGE (h)-[:USES_MARKETPLACE]->(m)
                )
                """,
                {"rows": handle_rows},
            )

    if wallets:
        wallet_rows = [
            w
            for w in wallets
            if w.get("address") and w.get("associated_handle") and w.get("handle_id") and w.get("handle_id")
        ]

        if wallet_rows:
            neo4j_conn.write(
                """
                UNWIND $rows AS row

                MERGE (w:Wallet {address: row.address})
                SET w.currency = row.currency

                MERGE (h:Handle {handle_id: row.handle_id})
                SET h.handle = row.associated_handle

                MERGE (h)-[:USED_WALLET]->(w)
                """,
                {"rows": wallet_rows},
            )


def sync_pgp_and_trust_graph(
    handles: List[Dict[str, Any]],
    trust_links: List[Dict[str, Any]],
) -> None:
    """Synchronize normalized PGP keys and synthetic trust relationships."""

    handle_rows = [
        row for row in handles
        if row.get("handle_id") and row.get("handle") and row.get("actor_id")
    ]

    if handle_rows:
        neo4j_conn.write(
            """
            UNWIND $rows AS row
            MATCH (h:Handle {handle_id: row.handle_id})
            SET h.pgp_fingerprint = row.pgp_fingerprint

            FOREACH (
                fingerprint IN CASE
                    WHEN row.pgp_fingerprint IS NULL OR row.pgp_fingerprint = ""
                    THEN []
                    ELSE [toUpper(row.pgp_fingerprint)]
                END |
                    MERGE (p:PGPKey {fingerprint: fingerprint})
                    SET p.key_type = "OpenPGP",
                        p.source = "synthetic_dataset"
                    MERGE (h)-[:HAS_PGP_KEY]->(p)
            )
            """,
            {"rows": handle_rows},
        )

    if not trust_links:
        return

    by_id = {
        str(row.get("handle_id")): row
        for row in handles
        if row.get("handle_id") is not None
    }

    rows = []
    for link in trust_links:
        source = by_id.get(str(link.get("source_handle_id")))
        target = by_id.get(str(link.get("target_handle_id")))
        if not source or not target:
            continue
        if not source.get("handle") or not target.get("handle"):
            continue

        rows.append({
            "source_handle_id": str(source["handle_id"]),
            "source_handle": source["handle"],
            "target_handle_id": str(target["handle_id"]),
            "target_handle": target["handle"],
            "source_pgp_fingerprint": (
                str(source.get("pgp_fingerprint") or "").strip().upper()
                or None
            ),
            "relationship_type": link.get("relationship_type") or "trust",
            "source": link.get("source") or "synthetic_dataset",
            "confidence": float(link.get("confidence") or 0.75),
            "first_seen": link.get("first_seen"),
            "last_seen": link.get("last_seen"),
        })

    if not rows:
        return

    neo4j_conn.write(
        """
        UNWIND $rows AS row

        MATCH (source:Handle {handle_id: row.source_handle_id})
        MATCH (target:Handle {handle_id: row.target_handle_id})

        MERGE (source)-[t:TRUSTS]->(target)
        SET t.relationship_type = row.relationship_type,
            t.source = row.source,
            t.confidence = row.confidence,
            t.first_seen = row.first_seen,
            t.last_seen = row.last_seen

        FOREACH (
            fingerprint IN CASE
                WHEN row.source_pgp_fingerprint IS NULL
                THEN []
                ELSE [row.source_pgp_fingerprint]
            END |
                MERGE (p:PGPKey {fingerprint: fingerprint})
                SET p.key_type = "OpenPGP",
                    p.source = row.source
                MERGE (source)-[:HAS_PGP_KEY]->(p)
                MERGE (p)-[pt:TRUSTS]->(target)
                SET pt.relationship_type = row.relationship_type,
                    pt.source = row.source,
                    pt.confidence = row.confidence,
                    pt.first_seen = row.first_seen,
                    pt.last_seen = row.last_seen
        )
        """,
        {"rows": rows},
    )


def sync_actor_observations(
    actor_id: str,
    observations: List[Dict[str, Any]],
) -> None:
    """
    Add evidence observations to Neo4j.

    Observation targets may be:
        actor_id
        primary handle
        associated handle
        infrastructure target

    Infrastructure-style observations also create an Infrastructure node.
    """

    if not observations:
        return

    rows = []

    infrastructure_types = {
        "infrastructure",
        "tls",
        "ssl",
        "ssl_cert_reuse",
        "certificate",
        "banner",
        "banner_reuse",
        "descriptor_timing",
        "uptime",
        "service",
        "port",
    }

    for obs in observations:
        observation_id = obs.get("observation_id")

        if not observation_id:
            continue

        indicator_type = obs.get("indicator_type") or "unknown"

        rows.append(
            {
                "observation_id": observation_id,
                "actor_id": actor_id,
                "indicator_type": indicator_type,
                "detected": bool(obs.get("detected", True)),
                "value": obs.get("value"),
                "target": obs.get("target"),
                "source": obs.get("source"),
                "confidence": obs.get("confidence"),
                "description": obs.get("description"),
                "timestamp": obs.get("timestamp"),
                "infrastructure": (
                    indicator_type.lower()
                    in infrastructure_types
                ),
            }
        )

    if not rows:
        return

    neo4j_conn.write(
        """
        UNWIND $rows AS row

        MATCH (a:Actor {actor_id: row.actor_id})

        MERGE (o:Observation {
            observation_id: row.observation_id
        })

        SET o.indicator_type = row.indicator_type,
            o.detected = row.detected,
            o.value = row.value,
            o.target = row.target,
            o.source = row.source,
            o.confidence = row.confidence,
            o.description = row.description,
            o.timestamp = row.timestamp

        MERGE (a)-[:HAS_OBSERVATION]->(o)

        WITH o, row

        FOREACH (
            ignored IN CASE
                WHEN row.infrastructure = true
                THEN [1]
                ELSE []
            END |

            MERGE (
                i:Infrastructure {
                    key: coalesce(
                        row.value,
                        row.target,
                        row.indicator_type
                    )
                }
            )

            SET i.indicator_type = row.indicator_type,
                i.value = row.value,
                i.target = row.target

            MERGE (o)-[:EVIDENCE_OF]->(i)
        )
        """,
        {"rows": rows},
    )


def get_actor_subgraph(
    actor_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Return a rich investigation subgraph.

    Includes:
        - actor
        - associated handles
        - wallets
        - marketplaces
        - observations
        - infrastructure
        - other handles sharing wallets

    Returns None when Neo4j is unavailable or the actor does not
    exist in Neo4j, allowing the API to use its Postgres fallback.
    """

    try:
        rows = neo4j_conn.query(
            """
            MATCH (a:Actor {actor_id: $actor_id})

            OPTIONAL MATCH (a)-[:USES_HANDLE]->(h:Handle)
            OPTIONAL MATCH (h)-[:USED_WALLET]->(w:Wallet)
            OPTIONAL MATCH (w)<-[:USED_WALLET]-(h2:Handle)

            OPTIONAL MATCH (h)-[:USES_MARKETPLACE]->(m:Marketplace)

            OPTIONAL MATCH (h)-[:HAS_PGP_KEY]->(p:PGPKey)
            OPTIONAL MATCH (h)-[t:TRUSTS]->(trusted:Handle)
            OPTIONAL MATCH (h)<-[ti:TRUSTS]-(trusting:Handle)

            OPTIONAL MATCH (a)-[:HAS_OBSERVATION]->(o:Observation)
            OPTIONAL MATCH (o)-[:EVIDENCE_OF]->(i:Infrastructure)

            RETURN
                a.actor_id AS actor_id,
                a.primary_handle AS primary_handle,

                collect(DISTINCT {handle_id: h.handle_id, handle: h.handle, platform: h.platform}) AS handle_nodes,

                collect(DISTINCT w.address) AS wallets,

                collect(DISTINCT {handle_id: h2.handle_id, handle: h2.handle, platform: h2.platform}) AS correlated_handle_nodes,

                collect(
                    DISTINCT {
                        wallet: w.address,
                        handle_id: h2.handle_id,
                        handle: h2.handle
                    }
                ) AS wallet_correlations,

                collect(DISTINCT m.name) AS marketplaces,

                collect(DISTINCT {
                    fingerprint: p.fingerprint,
                    key_type: p.key_type,
                    source: p.source
                }) AS pgp_keys,

                collect(DISTINCT {
                    handle_id: h.handle_id,
                    handle_id: h.handle_id,
                    handle: h.handle,
                    fingerprint: p.fingerprint
                }) AS handle_pgp_keys,

                collect(DISTINCT {
                    source_handle_id: h.handle_id,
                    source: h.handle,
                    target_handle_id: trusted.handle_id,
                    target: trusted.handle,
                    relationship_type: t.relationship_type,
                    confidence: t.confidence,
                    source_name: t.source,
                    first_seen: t.first_seen,
                    last_seen: t.last_seen
                }) AS trust_links_out,

                collect(DISTINCT {
                    source_handle_id: trusting.handle_id,
                    source: trusting.handle,
                    target_handle_id: h.handle_id,
                    target: h.handle,
                    relationship_type: ti.relationship_type,
                    confidence: ti.confidence,
                    source_name: ti.source,
                    first_seen: ti.first_seen,
                    last_seen: ti.last_seen
                }) AS trust_links_in,

collect(
    DISTINCT {
        handle_id: h.handle_id,
        handle_id: h.handle_id,
        handle: h.handle,
        marketplace: m.name
    }
) AS handle_marketplaces,

                collect(DISTINCT {
                    observation_id: o.observation_id,
                    indicator_type: o.indicator_type,
                    detected: o.detected,
                    value: o.value,
                    target: o.target,
                    source: o.source,
                    confidence: o.confidence,
                    description: o.description,
                    timestamp: o.timestamp
                }) AS observations,

                collect(DISTINCT {
                    key: i.key,
                    indicator_type: i.indicator_type,
                    value: i.value,
                    target: i.target
                }) AS infrastructure
            """,
            {"actor_id": actor_id},
        )

    except Exception:
        # Neo4j unavailable. Caller will use Postgres fallback.
        return None

    if not rows or not rows[0].get("actor_id"):
        return None

    row = rows[0]

    row["handle_nodes"] = [h for h in row.get("handle_nodes", []) if h and h.get("handle_id") and h.get("handle")]
    row["handles"] = [h["handle"] for h in row["handle_nodes"]]

    row["wallets"] = [
        w for w in row.get("wallets", [])
        if w
    ]

    row["correlated_handle_nodes"] = [h for h in row.get("correlated_handle_nodes", []) if h and h.get("handle_id") and h.get("handle") and h.get("handle") not in row["handles"]]
    row["correlated_handles"] = [h["handle"] for h in row["correlated_handle_nodes"]]
    row["wallet_correlations"] = [
        pair
        for pair in row.get("wallet_correlations", [])
        if (
            pair
            and pair.get("wallet")
            and pair.get("handle_id")
            and pair.get("handle")
            and pair.get("handle") not in row["handles"]
        )
    ]

    row["pgp_keys"] = [
        key for key in row.get("pgp_keys", [])
        if key and key.get("fingerprint")
    ]

    row["trust_links"] = [
        link for link in (
            row.get("trust_links_out", []) + row.get("trust_links_in", [])
        )
        if link and link.get("source") and link.get("target")
    ]

    row["marketplaces"] = [
        m for m in row.get("marketplaces", [])
        if m
    ]
    row["handle_marketplaces"] = [
    pair
    for pair in row.get("handle_marketplaces", [])
    if pair
    and pair.get("handle_id")
    and pair.get("handle")
    and pair.get("marketplace")
]

    row["observations"] = [
        o
        for o in row.get("observations", [])
        if o and o.get("observation_id")
    ]

    row["infrastructure"] = [
        i
        for i in row.get("infrastructure", [])
        if i and (
            i.get("key")
            or i.get("value")
            or i.get("target")
        )
    ]

    return row