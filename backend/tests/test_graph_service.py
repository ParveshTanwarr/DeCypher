"""
graph_service.py unit tests using a mocked Neo4j driver -- no live Neo4j
needed. Covers the fallback behavior that /actors/{id}/graph depends on.
"""
from unittest.mock import patch
from app.services import graph_service


def test_sync_actor_batch_issues_expected_writes():
    calls = []

    def fake_write(query, params):
        calls.append(params)

    with patch.object(graph_service.neo4j_conn, "write", side_effect=fake_write):
        graph_service.sync_actor_batch(
            actors=[{"actor_id": "A00001", "primary_handle": "nyxinhex99", "risk_category": "drugs"}],
            handles=[{"handle_id": "H00001", "handle": "nyxinhex99", "platform": "X", "actor_id": "A00001", "status": "active"}],
            wallets=[{"address": "w1", "handle_id": "H00001", "associated_handle": "nyxinhex99", "currency": "BTC"}],
        )

    assert len(calls) == 3


def test_get_actor_subgraph_returns_none_when_neo4j_unreachable():
    with patch.object(graph_service.neo4j_conn, "query", side_effect=Exception("connection refused")):
        result = graph_service.get_actor_subgraph("A00001")
    assert result is None


def test_get_actor_subgraph_returns_none_when_actor_not_synced():
    with patch.object(graph_service.neo4j_conn, "query", return_value=[]):
        result = graph_service.get_actor_subgraph("A00099")
    assert result is None


def test_get_actor_subgraph_returns_correlation_data():
    fake_row = {
        "actor_id": "A00001",
        "primary_handle": "nyxinhex99",
        "handle_nodes": [{"handle_id": "H00001", "handle": "nyxinhex99", "platform": "X"}, {"handle_id": "H00002", "handle": "vexatrace", "platform": "Y"}],
        "handles": ["nyxinhex99", "vexatrace"],
        "wallets": ["w1"],
        "correlated_handle_nodes": [{"handle_id": "H00009", "handle": "some_other_handle", "platform": "Z"}],
        "correlated_handles": ["some_other_handle"],
    }
    with patch.object(graph_service.neo4j_conn, "query", return_value=[fake_row]):
        result = graph_service.get_actor_subgraph("A00001")
    assert result["actor_id"] == "A00001"
    assert "vexatrace" in result["handles"]
    assert "some_other_handle" in result["correlated_handles"]


def test_sync_pgp_and_trust_graph_issues_expected_writes():
    calls = []

    def fake_write(query, params):
        calls.append(params)

    handles = [
        {
            "handle_id": "H00001",
            "actor_id": "A00001",
            "handle": "nyxinhex99",
            "pgp_fingerprint": "AA11",
        },
        {
            "handle_id": "H00003",
            "actor_id": "A00002",
            "handle": "zerylghost",
            "pgp_fingerprint": "BB22",
        },
    ]
    trust_links = [
        {
            "source_handle_id": "H00001",
            "target_handle_id": "H00003",
            "relationship_type": "trust",
            "confidence": 0.86,
            "source": "synthetic_dataset",
        }
    ]

    with patch.object(graph_service.neo4j_conn, "write", side_effect=fake_write):
        graph_service.sync_pgp_and_trust_graph(handles, trust_links)

    assert len(calls) == 2
    assert calls[0]["rows"][0]["pgp_fingerprint"] == "AA11"
    assert calls[1]["rows"][0]["source_handle"] == "nyxinhex99"
    assert calls[1]["rows"][0]["target_handle"] == "zerylghost"


def test_actor_graph_uses_postgres_fallback(client, admin_headers):
    with patch.object(graph_service, "get_actor_subgraph", return_value=None):
        response = client.get("/actors/A00001/graph", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["nodes"]
    assert payload["links"]
    actor_node = next(node for node in payload["nodes"] if node["id"] == "A00001")
    assert actor_node["properties"]["priority_score"] is not None


def test_graph_sync_uses_handle_id_when_names_collide():
    calls = []

    def fake_write(query, params):
        calls.append((query, params))

    with patch.object(graph_service.neo4j_conn, "write", side_effect=fake_write):
        graph_service.sync_actor_batch(
            actors=[
                {"actor_id": "A00001", "primary_handle": "shared", "risk_category": "drugs"},
                {"actor_id": "A00002", "primary_handle": "shared", "risk_category": "fraud"},
            ],
            handles=[
                {"handle_id": "H00001", "handle": "shared", "platform": "X", "actor_id": "A00001", "status": "active"},
                {"handle_id": "H00002", "handle": "shared", "platform": "Y", "actor_id": "A00002", "status": "active"},
            ],
            wallets=[],
        )

    query, params = calls[1]
    assert "MERGE (h:Handle {handle_id: row.handle_id})" in query
    assert {row["handle_id"] for row in params["rows"]} == {"H00001", "H00002"}


def test_temporal_graph_projection_uses_canonical_handle_identity():
    calls = []

    def fake_write(query, params):
        calls.append((query, params))

    events = [
        {
            "event_id": "handle:1:registered",
            "actor_id": "A00001",
            "event_type": "handle_registered",
            "entity_type": "handle",
            "entity_id": "1",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "source": "handles",
            "payload": {
                "graph_handle_id": "H00001",
                "handle": "nyxinhex99",
                "platform": "marketplace_11",
            },
        }
    ]

    with patch.object(graph_service.neo4j_conn, "write", side_effect=fake_write):
        graph_service.sync_temporal_events(events)

    assert len(calls) == 1
    query, params = calls[0]
    assert "row.payload.graph_handle_id" in query
    assert "row.payload.handle" in query
    assert "toString(row.entity_id)" not in query
    assert params["rows"][0]["payload"]["graph_handle_id"] == "H00001"
