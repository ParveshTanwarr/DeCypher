"""
Actor endpoint regression tests: exact-match ID lookups (the ilike
wildcard bug), pagination, and the evidence endpoint now having real data.
"""


def test_get_actors_returns_data(client, admin_headers):
    r = client.get("/actors", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_pagination_limit_and_offset(client, admin_headers):
    r = client.get("/actors", headers=admin_headers, params={"limit": 5})
    assert len(r.json()) == 5

    page1 = client.get("/actors", headers=admin_headers, params={"limit": 5, "offset": 0}).json()
    page2 = client.get("/actors", headers=admin_headers, params={"limit": 5, "offset": 5}).json()
    assert {a["actor_id"] for a in page1}.isdisjoint({a["actor_id"] for a in page2})


def test_exact_actor_lookup_works(client, admin_headers):
    r = client.get("/actors/A00001", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["actor_id"] == "A00001"


def test_wildcard_characters_do_not_match_everything(client, admin_headers):
    """
    Actor.actor_id.ilike(actor_id) used to treat literal '%'/'_' in the
    path parameter as SQL wildcards instead of an exact identifier.
    """
    r = client.get("/actors/A%", headers=admin_headers)
    assert r.status_code == 404

    r = client.get("/actors/A_____", headers=admin_headers)
    assert r.status_code == 404


def test_actor_not_found_returns_404(client, admin_headers):
    r = client.get("/actors/DOES_NOT_EXIST", headers=admin_headers)
    assert r.status_code == 404


def test_evidence_returns_seeded_observations(client, admin_headers):
    """
    A00358 is a known actor_id_ground_truth in infrastructure_indicators.csv --
    this previously always returned [] because that CSV was never ingested.
    """
    r = client.get("/actors/A00358/evidence", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) > 0
    assert "nan" not in r.json()[0]["description"].lower()


def test_graph_endpoint_falls_back_gracefully_without_neo4j(client, admin_headers):
    """Neo4j isn't running in the test environment -- this must not hang or 500."""
    r = client.get("/actors/A00001/graph", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["nodes"]) > 0
