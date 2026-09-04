"""
Neo4j correlation-graph service.

This was previously an empty stub -- nothing in the app ever imported
neo4j_client.py, so the platform's actual "graph" never got touched by
any request. This gives it a real (intentionally simple) schema so the
rest of the team has something working to build on:

    (:Actor {actor_id, primary_handle, risk_category})
    (:Handle {handle, platform, status})
    (:Wallet {address, currency})

    (Actor)-[:USES_HANDLE]->(Handle)
    (Handle)-[:USED_WALLET]->(Wallet)

The interesting part is USED_WALLET: it's keyed off the raw handle
string, independent of whatever actor_id Postgres has assigned. That's
what lets get_actor_subgraph() surface *other* handles that reused one
of this actor's wallets -- i.e. the actual Level 1 correlation signal
described in data/README.md, not just a flat "actor -> its own stuff"
star graph.

Once the Graph/Data lead's finalized schema and cluster-detection
Cypher land, this can be extended or replaced -- the important part for
now is that Neo4j is actually wired into the request path.
"""

from typing import Any, Dict, List, Optional

from app.database.neo4j_client import neo4j_conn


def sync_actor_batch(
    actors: List[Dict[str, Any]],
    handles: List[Dict[str, Any]],
    wallets: List[Dict[str, Any]],
) -> None:
    """
    Bulk-upserts Actor/Handle/Wallet nodes and their relationships into
    Neo4j. Takes the same plain dicts the Postgres upserts build, so the
    ingestion pipeline can call this right after loading each CSV.
    Safe to call with partial/empty lists.
    """
    if actors:
        neo4j_conn.write(
            """
            UNWIND $rows AS row
            MERGE (a:Actor {actor_id: row.actor_id})
            SET a.primary_handle = row.primary_handle,
                a.risk_category = row.risk_category
            """,
            {"rows": actors},
        )

    if handles:
        handle_rows = [h for h in handles if h.get("handle") and h.get("actor_id")]
        if handle_rows:
            neo4j_conn.write(
                """
                UNWIND $rows AS row
                MERGE (h:Handle {handle: row.handle})
                SET h.platform = row.platform, h.status = row.status
                WITH h, row
                MATCH (a:Actor {actor_id: row.actor_id})
                MERGE (a)-[:USES_HANDLE]->(h)
                """,
                {"rows": handle_rows},
            )

    if wallets:
        wallet_rows = [w for w in wallets if w.get("address") and w.get("associated_handle")]
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


def get_actor_subgraph(actor_id: str) -> Optional[Dict[str, Any]]:
    """
    Real correlation query: this actor's own handles/wallets, PLUS any
    other handles that reused one of those wallets. Returns None (so
    the caller can fall back to the Postgres-built star graph) if Neo4j
    has no data yet for this actor -- e.g. before ingestion's Neo4j sync
    has been run, or if Neo4j isn't reachable.
    """
    try:
        rows = neo4j_conn.query(
            """
            MATCH (a:Actor {actor_id: $actor_id})
            OPTIONAL MATCH (a)-[:USES_HANDLE]->(h:Handle)
            OPTIONAL MATCH (h)-[:USED_WALLET]->(w:Wallet)
            OPTIONAL MATCH (w)<-[:USED_WALLET]-(h2:Handle)
            WHERE h2 IS NULL OR h2.handle <> h.handle
            RETURN a.actor_id AS actor_id,
                   a.primary_handle AS primary_handle,
                   collect(DISTINCT h.handle) AS handles,
                   collect(DISTINCT w.address) AS wallets,
                   collect(DISTINCT h2.handle) AS correlated_handles
            """,
            {"actor_id": actor_id},
        )
    except Exception:
        # Neo4j down/unreachable -- let the caller fall back to Postgres.
        return None

    if not rows or not rows[0].get("actor_id"):
        return None

    row = rows[0]
    row["handles"] = [h for h in row.get("handles", []) if h]
    row["wallets"] = [w for w in row.get("wallets", []) if w]
    row["correlated_handles"] = [h for h in row.get("correlated_handles", []) if h]
    return row
