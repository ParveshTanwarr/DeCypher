"""Tests for temporal evidence analytics and structural graph anomaly scoring."""

from app.services.graph_anomaly_service import GraphAnomalyService
from app.services.temporal_events import backfill_temporal_events, get_actor_timeline


def test_temporal_backfill_is_idempotent(client, analyst_headers):
    from app.database.postgres import SessionLocal

    db = SessionLocal()
    try:
        first = backfill_temporal_events(db, actor_id="A00001")
        db.commit()
        second = backfill_temporal_events(db, actor_id="A00001")
        db.commit()
        timeline = get_actor_timeline(db, "A00001", limit=25)
    finally:
        db.close()

    assert first >= 0
    assert second == 0
    assert timeline["actor_id"] == "A00001"
    assert timeline["total_events"] >= 1


def test_temporal_timeline_endpoint(client, analyst_headers):
    response = client.get(
        "/analytics/actors/A00001/timeline?limit=25",
        headers=analyst_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["actor_id"] == "A00001"
    assert payload["total_events"] >= 1
    assert "event_types" in payload
    assert all("timestamp" in item for item in payload["events"])


def test_graph_anomaly_service_returns_bounded_score():
    from app.database.postgres import SessionLocal

    db = SessionLocal()
    try:
        result = GraphAnomalyService(db).analyze("A00001")
    finally:
        db.close()

    assert 0.0 <= result["anomaly_score"] <= 100.0
    assert result["actor_id"] == "A00001"
    assert "features" in result
    assert "feature_percentiles" in result
    assert "methodology" in result


def test_graph_anomaly_endpoint(client, analyst_headers):
    response = client.get(
        "/analytics/actors/A00001/graph-anomaly",
        headers=analyst_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert 0.0 <= payload["anomaly_score"] <= 100.0
    assert "contributing_features" in payload


def test_graph_anomaly_leaderboard(client, analyst_headers):
    response = client.get(
        "/analytics/graph-anomalies?limit=5",
        headers=analyst_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_actors"] >= 1
    assert len(payload["results"]) <= 5


def test_temporal_events_project_to_neo4j_without_invalid_coalesce_endpoint():
    """Regression test for temporal Event->Handle projection in Neo4j."""
    from app.database.postgres import SessionLocal
    from app.models.sql_models import TemporalEvent
    from app.services import graph_service
    from app.services.temporal_events import backfill_temporal_events, sync_temporal_events_to_neo4j

    db = SessionLocal()
    try:
        backfill_temporal_events(db, actor_id="A00001")
        db.commit()
        event = (
            db.query(TemporalEvent)
            .filter(
                TemporalEvent.actor_id == "A00001",
                TemporalEvent.entity_type == "handle",
            )
            .order_by(TemporalEvent.id.asc())
            .first()
        )
        assert event is not None

        sync_temporal_events_to_neo4j(db, actor_id="A00001")

        rows = graph_service.neo4j_conn.query(
            """
            MATCH (e:Event {event_id: $event_id})-[:DESCRIBES]->(h:Handle)
            RETURN h.handle_id AS handle_id
            """,
            {"event_id": event.event_key},
        )
        assert rows
        assert rows[0]["handle_id"]
    finally:
        db.close()
