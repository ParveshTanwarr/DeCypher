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
