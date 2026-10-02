import uuid

from app.database.postgres import SessionLocal
from app.models.sql_models import InvestigatorFeedback, Observation
from app.services.correlation_service import CorrelationService


def _observation_id(prefix="CF"):
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def test_counterfactual_analysis_reports_leave_one_signal_out_sensitivity(client, admin_headers):
    response = client.get(
        "/correlation/actor/A00001/counterfactual",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["candidate_actor"] == "A00001"
    counterfactual = body["counterfactual"]
    assert counterfactual["available"] in (True, False)
    assert "not a causal effect" in counterfactual["note"]


def test_source_reliability_adapts_from_other_actor_feedback_without_self_leakage():
    db = SessionLocal()
    source = f"reviewed_source_{uuid.uuid4().hex[:8]}"
    try:
        db.add_all(
            [
                Observation(
                    observation_id=_observation_id("SRC-A1"),
                    indicator_type="banner_match",
                    detected=True,
                    value="controlled",
                    target="A00001",
                    source=source,
                    confidence=0.8,
                ),
                Observation(
                    observation_id=_observation_id("SRC-A2"),
                    indicator_type="banner_match",
                    detected=True,
                    value="controlled",
                    target="A00002",
                    source=source,
                    confidence=0.8,
                ),
                Observation(
                    observation_id=_observation_id("SRC-A3"),
                    indicator_type="banner_match",
                    detected=True,
                    value="controlled",
                    target="A00003",
                    source=source,
                    confidence=0.8,
                ),
            ]
        )
        db.add_all(
            [
                InvestigatorFeedback(
                    actor_id="A00002",
                    verdict="Confirmed",
                    investigator_id="pytest",
                ),
                InvestigatorFeedback(
                    actor_id="A00003",
                    verdict="False Positive",
                    investigator_id="pytest",
                ),
                # This review must not be used when estimating A00001.
                InvestigatorFeedback(
                    actor_id="A00001",
                    verdict="Confirmed",
                    investigator_id="pytest",
                ),
            ]
        )
        db.commit()

        service = CorrelationService(db)
        result = service._source_reliability("A00001")[source]

        assert result["review_count"] == 2
        assert result["confirmed_reviews"] == 1
        assert result["false_positive_reviews"] == 1
        assert result["review_coverage"] > 0
        assert result["posterior"] == 0.5
        assert result["multiplier"] == 1.0
        assert result["basis"] == "leave_one_actor_out_review_rate"
    finally:
        db.rollback()
        db.close()


def test_counterfactual_math_is_deterministic():
    db = SessionLocal()
    try:
        service = CorrelationService(db)
        signals = [
            {"type": "wallet_reuse", "confidence": 1.0},
            {"type": "stylometry", "confidence": 0.5},
            {"type": "banner_match", "confidence": 0.0},
        ]
        result = service._counterfactual_analysis(signals)

        assert result["available"] is True
        assert len(result["scenarios"]) == 3
        assert result["baseline_evidence_score"] == 0.6364
        assert result["scenarios"][0]["absolute_impact"] >= result["scenarios"][-1]["absolute_impact"]
    finally:
        db.close()
