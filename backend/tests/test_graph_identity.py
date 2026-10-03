from unittest.mock import patch

from app.services import graph_service


def test_actor_graph_sync_uses_stable_source_handle_ids(client, admin_headers):
    captured = {}

    def capture_batch(*, actors, handles, wallets):
        captured["handles"] = handles
        captured["wallets"] = wallets

    with (
        patch.object(graph_service, "sync_actor_batch", side_effect=capture_batch),
        patch.object(graph_service, "sync_pgp_and_trust_graph"),
        patch.object(graph_service, "sync_actor_observations"),
        patch.object(graph_service, "get_actor_subgraph", return_value=None),
    ):
        response = client.get("/actors/A00001/graph", headers=admin_headers)

    assert response.status_code == 200, response.text
    handle_ids = {row["handle_id"] for row in captured["handles"]}
    assert "H00001" in handle_ids
    assert "H00002" in handle_ids
    assert all(not str(value).isdigit() for value in handle_ids)
