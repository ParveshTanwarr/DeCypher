import base64


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

        response = client.get(f"/historical-cases/context/actor/{actor_id}", headers=admin_headers)
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
