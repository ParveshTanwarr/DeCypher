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
        assert "last_error" not in created
        assert query_secret not in created["url"]
        assert secret not in create_response.text

        list_response = client.get("/collection/sources", headers=analyst_headers)
        assert list_response.status_code == 200, list_response.text
        row = next(item for item in list_response.json() if item["name"] == name)
        assert "headers" not in row
        assert "parser_config" not in row
        assert "last_error" not in row
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



def test_collection_runs_redact_internal_error_details(client, admin_headers):
    from app.database.postgres import SessionLocal
    from app.models.advanced_models import CollectionRun, CollectionSource

    db = SessionLocal()
    source = None
    run = None
    try:
        source = CollectionSource(
            name="test-run-redaction-source",
            kind="json",
            url="http://localhost/intel",
            enabled=False,
            interval_minutes=15,
            next_run_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db.add(source)
        db.flush()
        run = CollectionRun(
            source_id=source.id,
            status="failed",
            items_seen=0,
            observations_created=0,
            entities_created=0,
            error="GET http://localhost/intel?api_key=SUPER-SECRET failed",
        )
        db.add(run)
        db.commit()
        run_id = run.id
        source_id = source.id
    finally:
        db.close()

    try:
        response = client.get("/collection/runs", headers=admin_headers)
        assert response.status_code == 200, response.text
        row = next(item for item in response.json() if item["id"] == run_id)
        assert "error" not in row
        assert "SUPER-SECRET" not in response.text
    finally:
        db = SessionLocal()
        try:
            if run is not None:
                db.query(CollectionRun).filter(CollectionRun.id == run_id).delete()
            if source_id is not None:
                db.query(CollectionSource).filter(CollectionSource.id == source_id).delete()
            db.commit()
        finally:
            db.close()


def test_actor_identifier_case_is_normalized_across_core_reads(client, admin_headers):
    correlation = client.get("/correlation/actor/a00001", headers=admin_headers)
    assert correlation.status_code == 200, correlation.text
    assert correlation.json()["candidate_actor"] == "A00001"

    timeline = client.get("/analytics/actors/a00001/timeline", headers=admin_headers)
    assert timeline.status_code == 200, timeline.text
    assert timeline.json()["actor_id"] == "A00001"


def test_timeline_get_does_not_materialize_rows(client, admin_headers):
    from app.database.postgres import SessionLocal
    from app.models.sql_models import TemporalEvent

    db = SessionLocal()
    try:
        before = db.query(TemporalEvent).count()
    finally:
        db.close()

    response = client.get("/analytics/actors/A00001/timeline", headers=admin_headers)
    assert response.status_code == 200, response.text

    db = SessionLocal()
    try:
        after = db.query(TemporalEvent).count()
    finally:
        db.close()

    assert after == before



def test_collection_pipeline_resolves_entities_and_exposes_candidate_graph_link(client, admin_headers, monkeypatch):
    """A source item must flow through observation, entity, linkage and graph layers."""
    import json
    from uuid import uuid4
    from datetime import datetime, timezone
    from app.database.postgres import SessionLocal
    from app.models.advanced_models import CollectionRun, CollectionSource, EntityLink, ExternalEntity
    from app.models.sql_models import Observation
    from app.services.advanced_intelligence import CollectionService

    source_name = f"p0-e2e-{uuid4().hex[:10]}"
    source_url = "http://localhost/authorized-fixture.json"
    source_label = f"collection:{source_name}"
    source_id = None
    observation_id = None
    db = SessionLocal()
    try:
        source = CollectionSource(
            name=source_name,
            kind="json",
            url=source_url,
            actor_id=None,
            enabled=False,
            interval_minutes=15,
            headers={},
            parser_config={},
            next_run_at=datetime.now(timezone.utc),
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        source_id = source.id

        fixture = [{
            "title": "P0 pipeline fixture",
            "description": "Observed public alias @nyxinhex99 for candidate resolution.",
        }]
        monkeypatch.setattr(
            CollectionService,
            "_request",
            lambda self, configured_source: (
                200,
                "application/json",
                json.dumps(fixture),
            ),
        )

        result = CollectionService(db).run_source(source)
        assert result["items_seen"] == 1
        assert result["observations_created"] == 1
        assert result["entities_created"] >= 1

        entity = (
            db.query(ExternalEntity)
            .filter(
                ExternalEntity.source == source_label,
                ExternalEntity.entity_type == "handle",
                ExternalEntity.canonical_value == "nyxinhex99",
            )
            .first()
        )
        assert entity is not None
        link = (
            db.query(EntityLink)
            .filter(
                EntityLink.actor_id == "A00001",
                EntityLink.entity_id == entity.id,
            )
            .first()
        )
        assert link is not None
        assert link.match_type == "exact_handle"
        assert link.explanation["identity_status"] == "candidate_only"

        graph = client.get("/actors/A00001/graph", headers=admin_headers)
        assert graph.status_code == 200, graph.text
        body = graph.json()
        assert any(
            node["category"] == "ExternalEntity"
            and node["name"] == "nyxinhex99"
            for node in body["nodes"]
        )
        assert any(
            edge["relation"] == "POSSIBLE_MATCH"
            and edge["source"] == "A00001"
            for edge in body["links"]
        )

        observation_id = f"collect_{source_id}_"
        assert db.query(Observation).filter(
            Observation.observation_id.like(observation_id + "%")
        ).count() == 1
    finally:
        db.rollback()
        if source_id is not None:
            db.query(CollectionRun).filter(CollectionRun.source_id == source_id).delete(synchronize_session=False)
            db.query(EntityLink).filter(EntityLink.entity_id.in_(
                db.query(ExternalEntity.id).filter(ExternalEntity.source == source_label)
            )).delete(synchronize_session=False)
            db.query(Observation).filter(Observation.observation_id.like(f"collect_{source_id}_%")).delete(synchronize_session=False)
            db.query(ExternalEntity).filter(ExternalEntity.source == source_label).delete(synchronize_session=False)
            db.query(CollectionSource).filter(CollectionSource.id == source_id).delete(synchronize_session=False)
            db.commit()
        db.close()
