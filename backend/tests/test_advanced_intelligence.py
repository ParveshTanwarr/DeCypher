import base64
from types import SimpleNamespace

import pytest


PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_merkle_status_and_media_fingerprint(client, admin_headers):
    status = client.get("/integrity/merkle-status", headers=admin_headers)
    assert status.status_code == 200, status.text
    assert status.json()["blockchain_mode"] == "internal_merkle_blockchain_style_ledger"

    response = client.post(
        "/media/fingerprint",
        headers=admin_headers,
        json={
            "media_id": "test-image-a",
            "data_url": f"data:image/png;base64,{PNG_1X1}",
            "source": "test",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["phash"]
    assert body["sha256"]

    compared = client.post(
        "/media/compare",
        headers=admin_headers,
        json={"media_a": "test-image-a", "media_b": "test-image-a"},
    )
    assert compared.status_code == 200, compared.text
    assert compared.json()["exact_sha256_match"] is True


def test_evidence_ablation_requires_auth(client):
    response = client.post(
        "/correlation/actor/A00001/ablation",
        json={"disabled_signals": ["wallet_reuse"]},
    )
    assert response.status_code == 401


def test_collection_status_is_exposed(client, admin_headers):
    response = client.get("/collection/status", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "continuous_collection" in body
    assert "sources" in body


def test_historical_case_context_is_exposed_for_matching_actor(client, admin_headers):
    from app.database.postgres import SessionLocal
    from app.models.sql_models import Actor, DarkWebHandle

    db = SessionLocal()
    try:
        actor_id = "CASE-ALPHABAY-UI"
        db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor_id).delete()
        db.query(Actor).filter(Actor.actor_id == actor_id).delete()
        actor = Actor(actor_id=actor_id, primary_handle="Alpha02", risk_category="historical_case")
        db.add(actor)
        db.flush()
        db.add(
            DarkWebHandle(
                source_handle_id="CASE-ALPHABAY-UI-H001",
                actor_id=actor_id,
                handle="Alpha02",
                platform="AlphaBay",
            )
        )
        db.commit()

        response = client.get(f"/historical-cases/context/actor/{actor_id.lower()}", headers=admin_headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["matches"]
        match = next(item for item in body["matches"] if item["case_id"] == "alphabay-2017")
        assert "Alpha02" in match["matched_aliases"]
        assert match["matched_identities"][0]["documented_name"]
        assert match["provenance"]
        assert match["timeline"]
    finally:
        db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == "CASE-ALPHABAY-UI").delete()
        db.query(Actor).filter(Actor.actor_id == "CASE-ALPHABAY-UI").delete()
        db.commit()
        db.close()


def test_media_request_enforces_bounded_data_url(client, admin_headers):
    oversized = client.post(
        "/media/fingerprint",
        headers=admin_headers,
        json={
            "media_id": "oversized-image",
            "data_url": "data:image/png;base64," + ("A" * 7_000_001),
            "source": "test",
        },
    )
    assert oversized.status_code == 422, oversized.text


def test_limited_response_reader_rejects_large_stream():
    from app.services.advanced_intelligence import _read_limited_response

    response = SimpleNamespace(
        headers={},
        iter_content=lambda chunk_size: [b"12345", b"67890"],
    )
    with pytest.raises(ValueError, match="exceeds configured"):
        _read_limited_response(response, 8)


def test_collection_sources_do_not_expose_stored_headers(client, admin_headers, analyst_headers):
    from uuid import uuid4
    from app.database.postgres import SessionLocal
    from app.models.advanced_models import CollectionSource

    name = f"test-secret-source-{uuid4().hex[:8]}"
    secret = "Bearer SUPER-SECRET-TEST-TOKEN"
    query_secret = "api_key=SUPER-SECRET-QUERY"
    create_response = None

    try:
        create_response = client.post(
            "/collection/sources",
            headers=admin_headers,
            json={
                "name": name,
                "kind": "json",
                "url": f"http://localhost/intel?{query_secret}",
                "headers": {"Authorization": secret},
                "parser_config": {"api_key": "SUPER-SECRET-CONFIG"},
            },
        )
        assert create_response.status_code == 200, create_response.text
        created = create_response.json()
        assert "headers" not in created
        assert "parser_config" not in created
        assert query_secret not in created["url"]
        assert secret not in create_response.text

        list_response = client.get("/collection/sources", headers=analyst_headers)
        assert list_response.status_code == 200, list_response.text
        row = next(item for item in list_response.json() if item["name"] == name)
        assert "headers" not in row
        assert "parser_config" not in row
        assert query_secret not in row["url"]
        assert secret not in list_response.text
        assert "SUPER-SECRET-CONFIG" not in list_response.text
    finally:
        db = SessionLocal()
        try:
            db.query(CollectionSource).filter(CollectionSource.name == name).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
