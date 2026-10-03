import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.postgres import SessionLocal
from app.models.advanced_models import EntityLink, ExternalEntity
from app.models.sql_models import Actor, DarkWebHandle
from app.services.advanced_intelligence import EntityLinkageService

CASE_PATH = Path(__file__).resolve().parents[2] / "data" / "historical_cases" / "alphabay_2017.json"


def _seed_case(db: Session):
    actor_ids = {
        "alphabay-cazes": "CASE-ALPHABAY-CAZES",
        "alphabay-wheeler": "CASE-ALPHABAY-WHEELER",
        "alphabay-herrell": "CASE-ALPHABAY-HERRELL",
    }
    db.query(EntityLink).delete()
    db.query(ExternalEntity).filter(ExternalEntity.source == "doj-alphabay-2017").delete()
    for actor_id in actor_ids.values():
        db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor_id).delete()
        db.query(Actor).filter(Actor.actor_id == actor_id).delete()

    rows = [
        ("CASE-ALPHABAY-CAZES", "Alpha02", "AlphaBay"),
        ("CASE-ALPHABAY-CAZES", "Admin", "AlphaBay"),
        ("CASE-ALPHABAY-WHEELER", "Trappy", "AlphaBay"),
        ("CASE-ALPHABAY-HERRELL", "Penissmith", "AlphaBay"),
        ("CASE-ALPHABAY-HERRELL", "Botah", "AlphaBay"),
    ]
    for actor_id, primary_handle, platform in [
        ("CASE-ALPHABAY-CAZES", "Alpha02", "AlphaBay"),
        ("CASE-ALPHABAY-WHEELER", "Trappy", "AlphaBay"),
        ("CASE-ALPHABAY-HERRELL", "Penissmith", "AlphaBay"),
    ]:
        db.add(Actor(actor_id=actor_id, primary_handle=primary_handle, risk_category="high"))

    db.flush()
    for alias in ("Alpha02", "Admin", "Trappy", "Penissmith", "Botah"):
        db.add(
            ExternalEntity(
                entity_type="handle",
                canonical_value=alias,
                display_name=alias,
                source="doj-alphabay-2017",
                confidence=1.0,
                entity_metadata={"case_id": "alphabay-2017-cazes", "evidence_type": "documented_alias"},
            )
        )
    db.flush()
    for index, (actor_id, handle, platform) in enumerate(rows, start=1):
        db.add(
            DarkWebHandle(
                source_handle_id=f"CASE-ALPHABAY-H{index}",
                actor_id=actor_id,
                handle=handle,
                platform=platform,
            )
        )
    db.commit()


def test_alphabay_public_case_entity_linkage():
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    assert case["case_id"] == "alphabay-2017-cazes"

    db = SessionLocal()
    try:
        _seed_case(db)

        alpha_links = EntityLinkageService(db).link_actor("CASE-ALPHABAY-CAZES")
        alpha_values = {row["canonical_value"] for row in alpha_links}
        assert {"alpha02", "admin"} <= {value.lower() for value in alpha_values}

        herrell_links = EntityLinkageService(db).link_actor("CASE-ALPHABAY-HERRELL")
        herrell_values = {row["canonical_value"] for row in herrell_links}
        assert {"penissmith", "botah"} <= {value.lower() for value in herrell_values}

        # The exact-link engine must not cross-link aliases documented for
        # distinct people merely because they share the AlphaBay platform.
        wheeler_links = EntityLinkageService(db).link_actor("CASE-ALPHABAY-WHEELER")
        wheeler_values = {row["canonical_value"].lower() for row in wheeler_links}
        assert "alpha02" not in wheeler_values
        assert "admin" not in wheeler_values
        assert "trappy" not in {value.lower() for value in alpha_values}
    finally:
        for actor_id in (
            "CASE-ALPHABAY-CAZES",
            "CASE-ALPHABAY-WHEELER",
            "CASE-ALPHABAY-HERRELL",
        ):
            db.query(EntityLink).filter(EntityLink.actor_id == actor_id).delete()
            db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor_id).delete()
            db.query(Actor).filter(Actor.actor_id == actor_id).delete()
        db.query(ExternalEntity).filter(ExternalEntity.source == "doj-alphabay-2017").delete()
        db.commit()
        db.close()
