from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.sql_models import Actor, DarkWebHandle

CASE_DIR = Path(__file__).resolve().parents[3] / "data" / "historical_cases"


class HistoricalCaseService:
    """Read-only registry for documented public-case context.

    Case manifests are provenance artifacts, not seeded production actors.
    They are surfaced in investigator views only when an actor's recorded
    handles match documented aliases in a manifest.
    """

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not payload.get("case_id"):
            raise ValueError(f"Invalid historical-case manifest: {path.name}")
        payload["_path"] = str(path)
        return payload

    @classmethod
    def list_cases(cls) -> list[dict[str, Any]]:
        if not CASE_DIR.exists():
            return []
        cases = []
        for path in sorted(CASE_DIR.glob("*.json")):
            try:
                case = cls._load(path)
            except Exception:
                continue
            cases.append({
                "case_id": case["case_id"],
                "case_name": case.get("case_name"),
                "provenance_count": len(case.get("provenance", [])),
                "identity_count": len(case.get("identities", [])),
                "timeline_event_count": len(case.get("timeline", [])),
                "limitations": case.get("model_limitations", []),
            })
        return cases

    @classmethod
    def get_case(cls, case_id: str) -> dict[str, Any] | None:
        if not CASE_DIR.exists():
            return None
        for path in CASE_DIR.glob("*.json"):
            try:
                case = cls._load(path)
            except Exception:
                continue
            if str(case.get("case_id", "")).lower() == case_id.lower():
                case.pop("_path", None)
                return case
        return None

    @staticmethod
    def _identity_matches(identity: dict[str, Any], normalized_handles: set[str]) -> list[str]:
        aliases = [str(alias) for alias in identity.get("aliases", [])]
        return [alias for alias in aliases if alias.strip().lower() in normalized_handles]

    @classmethod
    def match_handles(
        cls,
        handles: Iterable[str],
    ) -> list[dict[str, Any]]:
        normalized = {
            str(handle).strip().lower()
            for handle in handles
            if str(handle).strip()
        }
        if not normalized:
            return []

        matches: list[dict[str, Any]] = []
        for summary in cls.list_cases():
            case = cls.get_case(summary["case_id"])
            if not case:
                continue
            identity_matches = []
            for identity in case.get("identities", []):
                matched_aliases = cls._identity_matches(identity, normalized)
                if matched_aliases:
                    identity_matches.append({
                        "identity_id": identity.get("identity_id"),
                        "documented_name": identity.get("documented_name"),
                        "aliases": identity.get("aliases", []),
                        "matched_aliases": matched_aliases,
                        "role": identity.get("role"),
                    })
            if not identity_matches:
                continue

            matched_event_entities = {
                alias
                for identity in identity_matches
                for alias in identity.get("matched_aliases", [])
            }
            timeline = [
                {
                    **event,
                    "case_context": True,
                    "matched_identity": next(
                        (
                            item.get("identity_id")
                            for item in identity_matches
                            if event.get("identity_id") == item.get("identity_id")
                        ),
                        None,
                    ),
                }
                for event in case.get("timeline", [])
                if event.get("identity_id") in {item.get("identity_id") for item in identity_matches}
            ]

            matches.append({
                "case_id": case["case_id"],
                "case_name": case.get("case_name"),
                "matched_identities": identity_matches,
                "provenance": case.get("provenance", []),
                "timeline": timeline,
                "expected_same_identity_pairs": case.get("expected_same_identity_pairs", []),
                "expected_different_identity_pairs": case.get("expected_different_identity_pairs", []),
                "model_limitations": case.get("model_limitations", []),
                "matched_aliases": sorted(matched_event_entities),
                "validation_summary": {
                    "positive_control_pairs": len(case.get("expected_same_identity_pairs", [])),
                    "negative_control_pairs": len(case.get("expected_different_identity_pairs", [])),
                    "modules": [
                        "documented alias/entity linkage",
                        "chronological event reconstruction",
                        "evidence-ledger integrity",
                        "graph/anomaly context",
                    ],
                    "stylometry_status": (
                        "not validated on this case: original post corpus is not present in the repository"
                        if any("post corpus" in str(item).lower() for item in case.get("model_limitations", []))
                        else "available"
                    ),
                },
            })
        return matches

    @classmethod
    def match_actor(cls, db: Session, actor_id: str) -> list[dict[str, Any]]:
        actor = db.query(Actor).filter(func.lower(Actor.actor_id) == actor_id.lower()).first()
        if actor is None:
            return []
        handles = (
            db.query(DarkWebHandle.handle)
            .filter(DarkWebHandle.actor_id == actor.actor_id)
            .all()
        )
        names = [actor.primary_handle] + [row[0] for row in handles if row[0]]
        return cls.match_handles(names)
