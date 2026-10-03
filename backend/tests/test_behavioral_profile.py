def test_behavioral_profile_refresh_returns_evidence_backed_dimensions(client, admin_headers):
    response = client.post(
        "/actors/A00001/behavioral-profile/refresh",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["actor_id"] == "A00001"
    assert body["profile_version"] == "1.2"
    assert body["coverage"]["total_dimensions"] == 5
    assert set(body["dimensions"]) == {
        "linguistic",
        "temporal_lifecycle",
        "operational",
        "interaction",
        "infrastructure",
    }
    assert body["dimensions"]["temporal_lifecycle"]["has_post_timestamps"] is True
    assert body["dimensions"]["temporal_lifecycle"]["post_activity"]["available"] is True
    assert body["dimensions"]["temporal_lifecycle"]["post_activity"]["timestamped_post_count"] > 0
    assert any("synthetic" in item.lower() for item in body["limitations"])
    assert body["summary"]["linked_handle_count"] >= 1
    assert body["dimensions"]["linguistic"]["aggregation_method"] == "post_weighted"
    assert "handle_mean_features" in body["dimensions"]["linguistic"]
    assert body["generated_at"]
    assert body["source_fingerprint"]
    assert body["behavioral_drift"]["available"] is False

    latest = client.get("/actors/A00001/behavioral-profile", headers=admin_headers)
    assert latest.status_code == 200
    assert latest.json()["source_fingerprint"] == body["source_fingerprint"]


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


def test_profile_snapshot_comparison_reports_descriptive_changes():
    from app.services.behavioral_profile_service import BehavioralProfileService

    previous = {
        "dimensions": {
            "linguistic": {"features": {"type_token_ratio": 0.42, "average_word_length": 4.1}},
            "operational": {"marketplace_count": 2, "wallet_count": 3},
            "temporal_lifecycle": {"observed_span_days": 14, "overlapping_handle_windows": 1, "future_dated_handle_count": 0},
            "interaction": {"trust_link_count": 2, "outgoing_count": 1, "incoming_count": 1, "distinct_counterparty_handles": 2, "average_confidence": 0.70},
            "infrastructure": {"observation_count": 4, "mean_observation_confidence": 0.80},
        }
    }
    current = {
        "dimensions": {
            "linguistic": {"features": {"type_token_ratio": 0.51, "average_word_length": 4.1}},
            "operational": {"marketplace_count": 3, "wallet_count": 3},
            "temporal_lifecycle": {"observed_span_days": 21, "overlapping_handle_windows": 2, "future_dated_handle_count": 0},
            "interaction": {"trust_link_count": 3, "outgoing_count": 2, "incoming_count": 1, "distinct_counterparty_handles": 3, "average_confidence": 0.75},
            "infrastructure": {"observation_count": 5, "mean_observation_confidence": 0.82},
        }
    }
    result = BehavioralProfileService._compare_profiles(
        previous,
        current,
        "2026-10-01T12:00:00+00:00",
    )

    assert result["available"] is True
    assert result["linguistic_feature_deltas"] == [
        {
            "feature": "type_token_ratio",
            "previous": 0.42,
            "current": 0.51,
            "delta": 0.09,
        }
    ]
    assert result["operational_changes"]["marketplace_count"]["delta"] == 1
    assert result["lifecycle_changes"]["observed_span_days"]["delta"] == 7
    assert result["interaction_changes"]["trust_link_count"]["delta"] == 1
    assert result["infrastructure_changes"]["observation_count"]["delta"] == 1
    assert "not an anomaly verdict" in result["note"]



def test_activity_profile_uses_real_source_timestamps_without_inventing_them(monkeypatch):
    import pandas as pd
    from app.services.nlp_service import nlp_service

    posts = pd.DataFrame({
        "_handle_id": ["H-TIME-1", "H-TIME-1", "H-TIME-1", "H-TIME-2"],
        "_content": ["one", "two", "three", "four"],
        "_timestamp": pd.to_datetime([
            "2026-09-01T08:00:00Z",
            "2026-09-01T10:00:00Z",
            "2026-09-02T08:00:00Z",
            None,
        ], utc=True),
    })
    monkeypatch.setattr(nlp_service, "_posts_df", posts)
    monkeypatch.setattr(nlp_service, "_known_handle_ids", {"H-TIME-1", "H-TIME-2"})
    monkeypatch.setattr(nlp_service, "_name_to_handle_ids", {})

    result = nlp_service.activity_profile(["H-TIME-1", "H-TIME-2"])
    assert result["available"] is True
    assert result["timestamped_post_count"] == 3
    assert result["profiled_handle_count"] == 1
    row = result["per_handle"][0]
    assert row["active_days"] == 2
    assert row["median_inter_post_interval_hours"] == 12.0
    assert result["timezone"] == "UTC"
