from datetime import datetime, timedelta, timezone

from app.database.postgres import SessionLocal
from app.models.sql_models import Observation, ScanTarget, TemporalEvent
from app.services.graph_anomaly_service import _build_population
from app.services.temporal_events import materialize_temporal_events


def test_temporal_events_resolve_scan_target_url():
    db = SessionLocal()
    try:
        target_url = "https://scan-target-temporal-regression.example/"
        target_name = "TEMPORAL-REGRESSION-A00015"
        target = db.query(ScanTarget).filter(ScanTarget.name == target_name).first()
        if not target:
            target = ScanTarget(
                name=target_name,
                target_url=target_url,
                actor_id="A00015",
                enabled=True,
                interval_minutes=180,
                priority_aware=True,
                next_run_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.add(target)
            db.flush()

        observation_id = "TEMPORAL-SCAN-TARGET-A00015"
        existing = db.query(Observation).filter(
            Observation.observation_id == observation_id
        ).first()
        if not existing:
            db.add(
                Observation(
                    observation_id=observation_id,
                    indicator_type="infra_reuse",
                    detected=True,
                    value="regression-scan-target",
                    target=target_url,
                    source="pytest_temporal",
                    confidence=0.8,
                    description="Scan-target URL regression fixture",
                )
            )
        db.commit()

        materialize_temporal_events(db, actor_id="A00015")
        db.commit()

        event = db.query(TemporalEvent).filter(
            TemporalEvent.event_key == f"observation:{observation_id}"
        ).first()
        assert event is not None
        assert event.actor_id == "A00015"
    finally:
        db.close()


def test_graph_anomaly_resolves_scan_target_url_for_source_diversity():
    db = SessionLocal()
    try:
        target_url = "https://scan-target-anomaly-regression.example/"
        target_name = "ANOMALY-REGRESSION-A00016"
        target = db.query(ScanTarget).filter(ScanTarget.name == target_name).first()
        if not target:
            target = ScanTarget(
                name=target_name,
                target_url=target_url,
                actor_id="A00016",
                enabled=True,
                interval_minutes=180,
                priority_aware=True,
                next_run_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.add(target)
            db.flush()

        observation_id = "ANOMALY-SCAN-TARGET-A00016"
        existing = db.query(Observation).filter(
            Observation.observation_id == observation_id
        ).first()
        if not existing:
            db.add(
                Observation(
                    observation_id=observation_id,
                    indicator_type="external_infrastructure",
                    detected=True,
                    value="shared-regression-infra",
                    target=target_url,
                    source="pytest_anomaly_scan_target",
                    confidence=0.9,
                    description="Scan-target URL anomaly fixture",
                )
            )
        db.commit()

        population = _build_population(db)
        assert population["A00016"]["observation_source_diversity"] >= 1
    finally:
        db.close()
