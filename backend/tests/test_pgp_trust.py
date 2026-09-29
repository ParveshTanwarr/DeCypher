"""Regression tests for PGP-key normalization and trust-link correlation."""

from sqlalchemy import func

from app.models.sql_models import DarkWebHandle, PGPKey, TrustLink
from app.database.postgres import SessionLocal


def test_pgp_keys_and_trust_links_are_ingested():
    session = SessionLocal()
    try:
        pgp_count = session.query(func.count(PGPKey.id)).scalar()
        trust_count = session.query(func.count(TrustLink.id)).scalar()

        assert pgp_count >= 1
        assert trust_count >= 10

        handle = (
            session.query(DarkWebHandle)
            .filter(DarkWebHandle.handle == "nyxinhex99")
            .one()
        )
        assert len(handle.pgp_keys) == 1
        assert len(handle.trust_links_out) >= 1
    finally:
        session.close()


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


def test_global_search_finds_pgp_fingerprint(client, admin_headers):
    fingerprint = "0A998F3749EA8D26E6DFB1529C40566171E1B68B"
    response = client.get(
        "/search",
        params={"q": fingerprint[:12]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert any(
        result["type"] == "pgp_key"
        and result["matched_value"] == fingerprint
        for result in response.json()["results"]
    )
