"""Regression tests for PGP-key normalization and trust-link correlation."""

from sqlalchemy import func

from app.models.sql_models import DarkWebHandle, PGPKey, TrustLink


def test_pgp_keys_and_trust_links_are_ingested(db_session):
    pgp_count = db_session.query(func.count(PGPKey.id)).scalar()
    trust_count = db_session.query(func.count(TrustLink.id)).scalar()

    assert pgp_count >= 1
    assert trust_count >= 10

    handle = (
        db_session.query(DarkWebHandle)
        .filter(DarkWebHandle.handle == "nyxinhex99")
        .one()
    )
    assert len(handle.pgp_keys) == 1
    assert len(handle.trust_links_out) >= 1


def test_actor_detail_exposes_pgp_and_trust_links(client, admin_headers):
    response = client.get("/actors/A00001", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()

    assert payload["pgp_keys"]
    assert any(
        link["source"] == "nyxinhex99"
        for link in payload["trust_links"]
    )


def test_actor_graph_exposes_pgp_and_trust_relationships(client, admin_headers):
    response = client.get("/actors/A00001/graph", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()

    assert any(node["category"] == "PGPKey" for node in payload["nodes"])
    assert any(link["relation"] == "HAS_PGP_KEY" for link in payload["links"])
    assert any(link["relation"] == "TRUSTS" for link in payload["links"])
