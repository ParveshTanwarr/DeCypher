import uuid


def test_evidence_integrity_ledger_is_present_and_valid(client, admin_headers):
    status = client.get("/integrity/status", headers=admin_headers)
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["mode"] == "internal_hash_chain"
    assert body["blockchain_anchor_configured"] is False
    assert body["entry_count"] > 0
    assert len(body["head_hash"]) == 64

    verification = client.get("/integrity/verify", headers=admin_headers)
    assert verification.status_code == 200, verification.text
    result = verification.json()
    assert result["valid"] is True
    assert result["verified_entries"] == result["entry_count"]


def test_new_observations_are_chained_into_the_ledger(client, admin_headers):
    observation_id = f"LEDGER-TEST-{uuid.uuid4().hex[:10]}"
    payload = {
        "observations": [
            {
                "observation_id": observation_id,
                "indicator_type": "ledger_test",
                "detected": True,
                "value": "controlled-test-value",
                "target": "A00001",
                "source": "pytest",
                "confidence": 0.91,
                "description": "Controlled integrity-ledger test observation.",
            }
        ],
    }

    response = client.post("/scanner/observations", headers=admin_headers, json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["inserted_count"] == 1

    ledger = client.get("/integrity/ledger?limit=200", headers=admin_headers)
    assert ledger.status_code == 200, ledger.text
    entry = next(item for item in ledger.json()["entries"] if item["observation_id"] == observation_id)
    assert entry["event_type"] == "observation_ingested"
    assert len(entry["record_hash"]) == 64
    assert len(entry["previous_hash"]) == 64

    verification = client.get("/integrity/verify", headers=admin_headers)
    assert verification.status_code == 200
    assert verification.json()["valid"] is True


def test_ledger_verification_detects_tampering_and_recovery(client, admin_headers):
    from app.database.postgres import SessionLocal
    from app.models.sql_models import EvidenceLedgerEntry

    db = SessionLocal()
    try:
        entry = db.query(EvidenceLedgerEntry).order_by(EvidenceLedgerEntry.id.asc()).first()
        assert entry is not None
        original_hash = entry.record_hash
        entry.record_hash = "0" * 64
        db.commit()
    finally:
        db.close()

    tampered = client.get("/integrity/verify", headers=admin_headers)
    assert tampered.status_code == 200
    assert tampered.json()["valid"] is False

    db = SessionLocal()
    try:
        entry = db.query(EvidenceLedgerEntry).filter(EvidenceLedgerEntry.record_hash == "0" * 64).first()
        assert entry is not None
        entry.record_hash = original_hash
        db.commit()
    finally:
        db.close()

    recovered = client.get("/integrity/verify", headers=admin_headers)
    assert recovered.status_code == 200
    assert recovered.json()["valid"] is True


def test_evidence_integrity_requires_authentication(client):
    response = client.get("/integrity/verify")
    assert response.status_code == 401
