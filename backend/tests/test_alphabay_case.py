import json
from datetime import datetime, timezone
from pathlib import Path

from app.database.postgres import SessionLocal
from app.models.advanced_models import EntityLink, ExternalEntity
from app.models.sql_models import Actor, DarkWebHandle, EvidenceLedgerEntry, Observation, TemporalEvent
from app.services.advanced_intelligence import MerkleEvidenceService, EntityLinkageService
from app.services.evidence_ledger import EvidenceLedgerService
from app.services.graph_anomaly_service import GraphAnomalyService
from app.services.nlp_service import nlp_service
from app.services.temporal_events import backfill_temporal_events, get_actor_timeline

CASE_PATH = Path(__file__).resolve().parents[2] / "data" / "historical_cases" / "alphabay_2017.json"
CASE_SOURCE = "doj-alphabay-2017"

ACTORS = {
    "cazes": ("CASE-ALPHABAY-CAZES", "Alpha02"),
    "wheeler": ("CASE-ALPHABAY-WHEELER", "Trappy"),
    "herrell": ("CASE-ALPHABAY-HERRELL", "Penissmith"),
}


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _seed_case(db):
    actor_ids = [value[0] for value in ACTORS.values()]
    db.query(EntityLink).filter(EntityLink.actor_id.in_(actor_ids)).delete(synchronize_session=False)
    db.query(TemporalEvent).filter(TemporalEvent.actor_id.in_(actor_ids)).delete(synchronize_session=False)
    db.query(Observation).filter(Observation.source == CASE_SOURCE).delete(synchronize_session=False)
    db.query(ExternalEntity).filter(ExternalEntity.source == CASE_SOURCE).delete(synchronize_session=False)
    db.query(DarkWebHandle).filter(DarkWebHandle.actor_id.in_(actor_ids)).delete(synchronize_session=False)
    db.query(Actor).filter(Actor.actor_id.in_(actor_ids)).delete(synchronize_session=False)
    db.commit()

    actors = [
        Actor(actor_id="CASE-ALPHABAY-CAZES", primary_handle="Alpha02", risk_category="historical_case"),
        Actor(actor_id="CASE-ALPHABAY-WHEELER", primary_handle="Trappy", risk_category="historical_case"),
        Actor(actor_id="CASE-ALPHABAY-HERRELL", primary_handle="Penissmith", risk_category="historical_case"),
    ]
    db.add_all(actors)
    db.flush()

    handles = [
        DarkWebHandle(
            source_handle_id="CASE-AB-H001",
            actor_id="CASE-ALPHABAY-CAZES",
            handle="Alpha02",
            platform="AlphaBay",
            first_seen=_dt("2014-07-14T00:00:00Z"),
        ),
        DarkWebHandle(
            source_handle_id="CASE-AB-H002",
            actor_id="CASE-ALPHABAY-CAZES",
            handle="Admin",
            platform="AlphaBay",
            first_seen=_dt("2015-08-01T00:00:00Z"),
        ),
        DarkWebHandle(
            source_handle_id="CASE-AB-H003",
            actor_id="CASE-ALPHABAY-WHEELER",
            handle="Trappy",
            platform="AlphaBay",
            first_seen=_dt("2015-05-25T00:00:00Z"),
        ),
        DarkWebHandle(
            source_handle_id="CASE-AB-H004",
            actor_id="CASE-ALPHABAY-HERRELL",
            handle="Penissmith",
            platform="AlphaBay",
            first_seen=_dt("2018-01-01T00:00:00Z"),
        ),
        DarkWebHandle(
            source_handle_id="CASE-AB-H005",
            actor_id="CASE-ALPHABAY-HERRELL",
            handle="Botah",
            platform="AlphaBay",
            first_seen=_dt("2018-01-01T00:00:00Z"),
        ),
    ]
    db.add_all(handles)
    db.flush()

    aliases = ("Alpha02", "Admin", "Trappy", "Penissmith", "Botah")
    for alias in aliases:
        db.add(
            ExternalEntity(
                entity_type="handle",
                canonical_value=alias,
                display_name=alias,
                source=CASE_SOURCE,
                confidence=1.0,
                entity_metadata={
                    "case_id": "alphabay-2017",
                    "evidence_type": "documented_alias",
                },
            )
        )

    case_events = [
        ("cazes-indictment", "CASE-ALPHABAY-CAZES", "2017-06-01T00:00:00Z", "indictment", "Alexandre Cazes"),
        ("cazes-arrest", "CASE-ALPHABAY-CAZES", "2017-07-05T00:00:00Z", "arrest", "Alexandre Cazes"),
        ("alphabay-takedown", "CASE-ALPHABAY-CAZES", "2017-07-20T00:00:00Z", "marketplace_takedown", "AlphaBay"),
    ]
    for event_key, actor_id, timestamp, event_type, entity in case_events:
        db.add(
            TemporalEvent(
                event_key=f"case:{event_key}",
                actor_id=actor_id,
                event_type=event_type,
                entity_type="historical_case_fact",
                entity_id=entity,
                timestamp=_dt(timestamp),
                source=CASE_SOURCE,
                payload={"case_id": "alphabay-2017", "provenance": CASE_SOURCE},
            )
        )

    observations = [
        Observation(
            observation_id="CASE-AB-O001",
            indicator_type="historical_alias",
            detected=True,
            value="Alpha02 -> Admin",
            target="CASE-ALPHABAY-CAZES",
            source=CASE_SOURCE,
            timestamp=_dt("2015-08-01T00:00:00Z"),
            confidence=1.0,
            description="DOJ forfeiture complaint documents the Alpha02 account being renamed Admin in August 2015.",
        ),
        Observation(
            observation_id="CASE-AB-O002",
            indicator_type="historical_identity",
            detected=True,
            value="Cazes = Alpha02/Admin",
            target="CASE-ALPHABAY-CAZES",
            source=CASE_SOURCE,
            timestamp=_dt("2017-06-01T00:00:00Z"),
            confidence=1.0,
            description="DOJ indictment identifies Alexandre Cazes as Alpha02 and Admin.",
        ),
        Observation(
            observation_id="CASE-AB-O003",
            indicator_type="historical_role",
            detected=True,
            value="Trappy = Wheeler",
            target="CASE-ALPHABAY-WHEELER",
            source=CASE_SOURCE,
            timestamp=_dt("2015-05-25T00:00:00Z"),
            confidence=1.0,
            description="DOJ records Wheeler as Trappy and describes his AlphaBay public-relations role.",
        ),
        Observation(
            observation_id="CASE-AB-O004",
            indicator_type="historical_alias",
            detected=True,
            value="Penissmith = Botah",
            target="CASE-ALPHABAY-HERRELL",
            source=CASE_SOURCE,
            timestamp=_dt("2019-06-21T00:00:00Z"),
            confidence=1.0,
            description="DOJ records the AlphaBay moderator as using the monikers Penissmith and Botah.",
        ),
    ]
    db.add_all(observations)
    db.flush()
    EvidenceLedgerService(db).append_missing_for_observations(
        [
            {
                "observation_id": row.observation_id,
                "indicator_type": row.indicator_type,
                "detected": row.detected,
                "value": row.value,
                "target": row.target,
                "source": row.source,
                "timestamp": row.timestamp,
                "confidence": row.confidence,
                "description": row.description,
            }
            for row in observations
        ],
        created_by="alphabay_case_validation",
    )
    db.commit()


def test_alphabay_full_historical_case_validation():
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    assert case["case_id"] == "alphabay-2017"
    assert len(case["provenance"]) >= 4

    db = SessionLocal()
    try:
        _seed_case(db)

        # 1) Alias/entity linkage.
        cazes_links = EntityLinkageService(db).link_actor("CASE-ALPHABAY-CAZES")
        wheeler_links = EntityLinkageService(db).link_actor("CASE-ALPHABAY-WHEELER")
        herrell_links = EntityLinkageService(db).link_actor("CASE-ALPHABAY-HERRELL")

        assert {"alpha02", "admin"} <= {row["canonical_value"].lower() for row in cazes_links}
        assert {"trappy"} <= {row["canonical_value"].lower() for row in wheeler_links}
        assert {"penissmith", "botah"} <= {row["canonical_value"].lower() for row in herrell_links}

        # 2) Explicit negative controls: shared AlphaBay membership does not
        # collapse three documented people into one identity.
        cazes_values = {row["canonical_value"].lower() for row in cazes_links}
        wheeler_values = {row["canonical_value"].lower() for row in wheeler_links}
        herrell_values = {row["canonical_value"].lower() for row in herrell_links}
        assert "trappy" not in cazes_values
        assert not (cazes_values & herrell_values)
        assert not (wheeler_values & cazes_values)
        assert not (wheeler_values & herrell_values)

        # 3) Temporal materialization and chronology.
        for actor_id in ("CASE-ALPHABAY-CAZES", "CASE-ALPHABAY-WHEELER", "CASE-ALPHABAY-HERRELL"):
            backfill_temporal_events(db, actor_id=actor_id)
        db.commit()

        timeline = get_actor_timeline(db, "CASE-ALPHABAY-CAZES", limit=100)
        dates = [event["timestamp"] for event in timeline["events"] if event["event_type"] in {"indictment", "arrest", "marketplace_takedown"}]
        assert dates == sorted(dates, reverse=True)
        assert {"indictment", "arrest", "marketplace_takedown"} <= set(timeline["event_types"])

        # 4) Evidence integrity.
        ledger = EvidenceLedgerService(db).verify_chain()
        assert ledger["valid"] is True
        assert ledger["entry_count"] >= 4

        # 5) Merkle sealing over the actual persisted evidence chain.
        merkle = MerkleEvidenceService(db)
        merkle.seal_pending()
        db.commit()
        merkle_result = merkle.verify()
        assert merkle_result["valid"] is True
        assert merkle_result["entry_count"] >= 4

        # 6) Graph anomaly pipeline stays bounded and treats shared
        # marketplace membership as a structural context, not identity proof.
        anomaly = GraphAnomalyService(db).analyze("CASE-ALPHABAY-CAZES")
        assert 0.0 <= anomaly["anomaly_score"] <= 100.0
        assert "marketplace_switches" in anomaly["features"]
        assert "two_hop_trust_reach" in anomaly["features"]
        assert "temporal_event_density" in anomaly["features"]

        # 7) Stylometry is explicitly not claimed when the case fixture has no
        # original post corpus. The deployed engine reports insufficiency rather
        # than manufacturing a score from DOJ prose.
        stylometry = nlp_service.compare("Alpha02", "Admin")
        assert stylometry["similarity_score"] == 0.0
        assert stylometry["is_same_author"] is False
        assert "Insufficient sample text" in stylometry["error"]

    finally:
        db.rollback()
        db.close()
