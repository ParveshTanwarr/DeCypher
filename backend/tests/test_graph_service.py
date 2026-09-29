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
            handles=[{"handle": "nyxinhex99", "platform": "X", "actor_id": "A00001", "status": "active"}],
            wallets=[{"address": "w1", "associated_handle": "nyxinhex99", "currency": "BTC"}],
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
        "handles": ["nyxinhex99", "vexatrace"],
        "wallets": ["w1"],
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
