import base64
import uuid

import pytest
from fastapi import HTTPException

from app.database.postgres import SessionLocal
from app.models.sql_models import EvidenceLedgerEntry
from app.routers.ai import _actor_context


def _login(client, username, password):
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_inbound_trust_graph_uses_canonical_source_handle_id(client, admin_headers):
    response = client.get("/actors/A00002/graph", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    node_ids = {node["id"] for node in body["nodes"]}
    assert "handle:H00001" in node_ids
    assert "handle:H00003" in node_ids

    assert any(
        link["source"] == "handle:H00001"
        and link["target"] == "handle:H00003"
        and link["relation"] == "TRUSTS"
        for link in body["links"]
    )


def test_ai_actor_context_rejects_literal_sql_wildcards():
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc_info:
            _actor_context("A%", db)
        assert exc_info.value.status_code == 404
    finally:
        db.close()


def test_service_account_cannot_read_scanner_state(client):
    headers = _login(client, "scanner_service", "scanner_service_devkey_change_me")
    response = client.get("/scanner/targets", headers=headers)
    assert response.status_code == 403


def test_service_account_cannot_refresh_behavioral_profile(client):
    headers = _login(client, "scanner_service", "scanner_service_devkey_change_me")
    response = client.post(
        "/actors/A00001/behavioral-profile/refresh",
        headers=headers,
    )
    assert response.status_code == 403


def test_search_treats_like_wildcards_as_literals(client, admin_headers):
    response = client.get(
        "/search",
        headers=admin_headers,
        params={"q": "A%", "limit": 50},
    )
    assert response.status_code == 200, response.text
    assert response.json()["total_matches"] == 0
    assert response.json()["results"] == []


def test_duplicate_observation_id_does_not_duplicate_ledger(client, admin_headers):
    observation_id = f"DUPLICATE-LEDGER-{uuid.uuid4().hex[:12]}"
    payload = {
        "observations": [{
            "observation_id": observation_id,
            "indicator_type": "ledger_duplicate_test",
            "detected": True,
            "value": "first-value",
            "target": "A00001",
            "source": "pytest",
            "confidence": 0.9,
            "description": "First immutable observation payload.",
        }]
    }

    first = client.post("/scanner/observations", headers=admin_headers, json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["inserted_count"] == 1

    changed_payload = {
        **payload,
        "observations": [{
            **payload["observations"][0],
            "value": "different-value",
            "description": "Conflicting duplicate payload must be ignored.",
        }],
    }
    second = client.post(
        "/scanner/observations",
        headers=admin_headers,
        json=changed_payload,
    )
    assert second.status_code == 201, second.text
    assert second.json()["inserted_count"] == 0

    db = SessionLocal()
    try:
        count = (
            db.query(EvidenceLedgerEntry)
            .filter(EvidenceLedgerEntry.observation_id == observation_id)
            .count()
        )
        assert count == 1
    finally:
        db.close()


def test_large_graph_image_is_rejected(client, admin_headers):
    raw = b"x" * 5_000_001
    image = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    response = client.post(
        "/export/actor/A00001/report",
        headers=admin_headers,
        json={"graph_image": image},
    )
    assert response.status_code == 413
