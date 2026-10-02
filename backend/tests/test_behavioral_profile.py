def test_behavioral_profile_refresh_returns_evidence_backed_dimensions(client, admin_headers):
    response = client.post(
        "/actors/A00001/behavioral-profile/refresh",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["actor_id"] == "A00001"
    assert body["profile_version"] == "1.0"
    assert body["coverage"]["total_dimensions"] == 5
    assert set(body["dimensions"]) == {
        "linguistic",
        "temporal_lifecycle",
        "operational",
        "interaction",
        "infrastructure",
    }
    assert body["dimensions"]["temporal_lifecycle"]["has_post_timestamps"] is False
    assert any("synthetic" in item.lower() for item in body["limitations"])
    assert body["summary"]["linked_handle_count"] >= 1
    assert body["generated_at"]
    assert body["source_fingerprint"]


def test_behavioral_profile_refresh_is_idempotent_without_source_changes(client, admin_headers):
    first = client.post(
        "/actors/A00001/behavioral-profile/refresh",
        headers=admin_headers,
    )
    second = client.post(
        "/actors/A00001/behavioral-profile/refresh",
        headers=admin_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["source_fingerprint"] == second.json()["source_fingerprint"]
    assert len(second.json()["history"]) == 1


def test_behavioral_profile_requires_authentication(client):
    response = client.post("/actors/A00001/behavioral-profile/refresh")
    assert response.status_code == 401
