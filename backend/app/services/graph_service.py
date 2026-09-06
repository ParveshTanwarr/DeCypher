"""
Neo4j investigation graph service.

Graph schema:

    (:Actor)
    (:Handle)
    (:Wallet)
    (:Marketplace)
    (:Infrastructure)
    (:Observation)

Relationships:

    Actor -[:USES_HANDLE]-> Handle
    Handle -[:USED_WALLET]-> Wallet
    Handle -[:USES_MARKETPLACE]-> Marketplace
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
            if h.get("handle") and h.get("actor_id")
        ]

        if handle_rows:
            neo4j_conn.write(
                """
                UNWIND $rows AS row

                MERGE (h:Handle {handle: row.handle})
                SET h.platform = row.platform,
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
            if w.get("address") and w.get("associated_handle")
        ]

        if wallet_rows:
            neo4j_conn.write(
                """
                UNWIND $rows AS row

                MERGE (w:Wallet {address: row.address})
                SET w.currency = row.currency

                MERGE (h:Handle {handle: row.associated_handle})

                MERGE (h)-[:USED_WALLET]->(w)
                """,
                {"rows": wallet_rows},
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

            OPTIONAL MATCH (a)-[:HAS_OBSERVATION]->(o:Observation)
            OPTIONAL MATCH (o)-[:EVIDENCE_OF]->(i:Infrastructure)

            RETURN
                a.actor_id AS actor_id,
                a.primary_handle AS primary_handle,

                collect(DISTINCT h.handle) AS handles,

                collect(DISTINCT w.address) AS wallets,

                collect(DISTINCT h2.handle) AS correlated_handles,

                collect(
                    DISTINCT {
                        wallet: w.address,
                        handle: h2.handle
                    }
                ) AS wallet_correlations,

                collect(DISTINCT m.name) AS marketplaces,

collect(
    DISTINCT {
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

    row["handles"] = [
        h for h in row.get("handles", [])
        if h
    ]

    row["wallets"] = [
        w for w in row.get("wallets", [])
        if w
    ]

    row["correlated_handles"] = [
        h
        for h in row.get("correlated_handles", [])
        if h and h not in row["handles"]
    ]
    row["wallet_correlations"] = [
        pair
        for pair in row.get("wallet_correlations", [])
        if (
            pair
            and pair.get("wallet")
            and pair.get("handle")
            and pair.get("handle") not in row["handles"]
        )
    ]

    row["marketplaces"] = [
        m for m in row.get("marketplaces", [])
        if m
    ]
    row["handle_marketplaces"] = [
    pair
    for pair in row.get("handle_marketplaces", [])
    if pair
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