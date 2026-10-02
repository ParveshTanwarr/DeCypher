from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.sql_models import (
    Actor,
    BehavioralProfileSnapshot,
    DarkWebHandle,
    Observation,
    PGPKey,
    ScanTarget,
    TrustLink,
    Wallet,
    handle_pgp_keys,
)
from app.services.nlp_service import nlp_service
from app.services.observation_scope import build_observation_target_keys


PROFILE_VERSION = "1.0"


def _as_date(value: Optional[datetime]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def _counter_dict(values: Iterable[Optional[str]]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value).items()))


class BehavioralProfileService:
    """Builds an evidence-backed, descriptive behavioural profile for one actor."""

    def __init__(self, db: Session):
        self.db = db

    def build_profile(self, actor: Actor) -> Dict[str, Any]:
        handles = (
            self.db.query(DarkWebHandle)
            .options(joinedload(DarkWebHandle.pgp_keys))
            .filter(DarkWebHandle.actor_id == actor.actor_id)
            .order_by(DarkWebHandle.handle.asc())
            .all()
        )
        wallets = (
            self.db.query(Wallet)
            .filter(Wallet.actor_id == actor.actor_id)
            .all()
        )
        handle_ids = [handle.id for handle in handles]
        handle_names = [handle.handle for handle in handles]
        scan_targets = (
            self.db.query(ScanTarget)
            .filter(ScanTarget.actor_id == actor.actor_id)
            .all()
        )
        target_keys = build_observation_target_keys(
            actor.actor_id, actor.primary_handle, handles, scan_targets
        )
        observations = (
            self.db.query(Observation)
            .filter(
                func.lower(Observation.target).in_(target_keys),
                Observation.detected.is_(True),
                func.lower(Observation.source) != "synthetic_investigation_evidence",
            )
            .order_by(Observation.timestamp.asc())
            .all()
        )

        trust_links = []
        if handle_ids:
            trust_links = (
                self.db.query(TrustLink)
                .filter(
                    or_(
                        TrustLink.source_handle_id.in_(handle_ids),
                        TrustLink.target_handle_id.in_(handle_ids),
                    )
                )
                .all()
            )

        pgp_keys = {key.id: key for handle in handles for key in handle.pgp_keys}
        pgp_ids = list(pgp_keys)
        external_pgp_links = []
        if pgp_ids:
            external_pgp_links = (
                self.db.query(handle_pgp_keys.c.pgp_key_id, DarkWebHandle.id)
                .join(
                    DarkWebHandle,
                    DarkWebHandle.id == handle_pgp_keys.c.handle_id,
                )
                .filter(
                    handle_pgp_keys.c.pgp_key_id.in_(pgp_ids),
                    DarkWebHandle.actor_id != actor.actor_id,
                )
                .all()
            )

        wallet_addresses = sorted({wallet.address for wallet in wallets if wallet.address})
        external_wallet_rows = []
        if wallet_addresses:
            external_wallet_rows = (
                self.db.query(Wallet.address, Wallet.actor_id, Wallet.associated_handle)
                .filter(
                    Wallet.address.in_(wallet_addresses),
                    Wallet.actor_id.isnot(None),
                    Wallet.actor_id != actor.actor_id,
                )
                .all()
            )

        linguistic = nlp_service.profile_handles(handle_names)
        consistency = self._cross_handle_consistency(handle_names)

        lifecycle = self._lifecycle(handles)
        operational = self._operational(
            handles,
            wallets,
            pgp_keys,
            external_pgp_links,
            external_wallet_rows,
        )
        interaction = self._interaction(actor, handle_ids, trust_links)
        infrastructure = self._infrastructure(observations)

        dimension_flags = {
            "linguistic": bool(linguistic.get("available")),
            "temporal_lifecycle": bool(handles),
            "operational": bool(handles or wallets or pgp_keys),
            "interaction": bool(trust_links),
            "infrastructure": bool(observations),
        }
        available_dimensions = sum(dimension_flags.values())
        total_dimensions = len(dimension_flags)
        coverage_score = round(available_dimensions / total_dimensions, 3)

        patterns = []
        if len(handles) > 1:
            patterns.append(f"{len(handles)} linked account handles are recorded for this actor.")
        if operational["marketplace_count"] > 1:
            patterns.append(
                f"Linked handles span {operational['marketplace_count']} distinct marketplaces."
            )
        if operational["within_actor_wallet_reuse_count"]:
            patterns.append(
                f"{operational['within_actor_wallet_reuse_count']} wallet address(es) are reused across this actor's linked handles."
            )
        if operational["cross_actor_shared_wallet_count"]:
            patterns.append(
                f"{operational['cross_actor_shared_wallet_count']} wallet address(es) are also associated with other actor records."
            )
        if operational["pgp_reuse_across_other_handles_count"]:
            patterns.append(
                f"{operational['pgp_reuse_across_other_handles_count']} PGP key(s) are associated with handles outside this actor profile."
            )
        if interaction["trust_link_count"]:
            patterns.append(
                f"{interaction['trust_link_count']} trust relationship(s) connect this actor's handles to other handles."
            )
        if infrastructure["observation_count"]:
            patterns.append(
                f"{infrastructure['observation_count']} detected infrastructure observation(s) are linked to this actor."
            )
        if consistency["available"]:
            patterns.append(
                "Cross-handle linguistic similarity was evaluated using the configured authorship engine."
            )

        limitations = [
            "The bundled dataset is synthetic; this profile demonstrates prototype behaviour and is not real-world intelligence.",
            "The current post records do not provide usable per-post timestamps, so posting hours, weekday routines, and posting cadence are not inferred.",
            "Account creation and last-active dates describe account lifecycle windows, not continuous observed activity; future-dated synthetic records are not treated as current activity.",
            "Behavioural similarity and shared operational indicators are investigative leads, not proof of common identity.",
            "If the authorship model is unavailable, any fallback similarity is explicitly labelled and must not be treated as validated model output.",
        ]

        return {
            "actor_id": actor.actor_id,
            "profile_version": PROFILE_VERSION,
            "coverage": {
                "score": coverage_score,
                "available_dimensions": available_dimensions,
                "total_dimensions": total_dimensions,
                "dimensions": dimension_flags,
            },
            "summary": {
                "linked_handle_count": len(handles),
                "marketplace_count": operational["marketplace_count"],
                "wallet_count": len(wallets),
                "pgp_key_count": len(pgp_keys),
                "trust_link_count": len(trust_links),
                "infrastructure_observation_count": len(observations),
                "post_count": linguistic.get("sample_post_count", 0),
            },
            "dimensions": {
                "linguistic": {**linguistic, "cross_handle_consistency": consistency},
                "temporal_lifecycle": lifecycle,
                "operational": operational,
                "interaction": interaction,
                "infrastructure": infrastructure,
            },
            "patterns": patterns,
            "limitations": limitations,
            "data_sources": [
                "PostgreSQL actor and handle records",
                "Bundled synthetic marketplace posts via the existing NLP cache",
                "PostgreSQL wallet and PGP associations",
                "PostgreSQL trust-link records",
                "Detected, provenance-tagged infrastructure observations",
            ],
        }

    def refresh(self, actor: Actor) -> Dict[str, Any]:
        profile = self.build_profile(actor)
        canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"), default=str)
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        snapshot = (
            self.db.query(BehavioralProfileSnapshot)
            .filter(
                BehavioralProfileSnapshot.actor_id == actor.actor_id,
                BehavioralProfileSnapshot.source_fingerprint == fingerprint,
            )
            .first()
        )
        if snapshot is None:
            snapshot = BehavioralProfileSnapshot(
                actor_id=actor.actor_id,
                profile_version=PROFILE_VERSION,
                source_fingerprint=fingerprint,
                coverage_score=profile["coverage"]["score"],
                profile_data=profile,
            )
            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)

        return self._with_history(snapshot)

    def latest(self, actor_id: str) -> Optional[Dict[str, Any]]:
        snapshot = (
            self.db.query(BehavioralProfileSnapshot)
            .filter(BehavioralProfileSnapshot.actor_id == actor_id)
            .order_by(BehavioralProfileSnapshot.generated_at.desc())
            .first()
        )
        return self._with_history(snapshot) if snapshot else None

    def _with_history(self, snapshot: BehavioralProfileSnapshot) -> Dict[str, Any]:
        history_rows = (
            self.db.query(BehavioralProfileSnapshot)
            .filter(BehavioralProfileSnapshot.actor_id == snapshot.actor_id)
            .order_by(BehavioralProfileSnapshot.generated_at.desc())
            .limit(10)
            .all()
        )
        result = dict(snapshot.profile_data or {})
        result.update(
            {
                "generated_at": (
                    snapshot.generated_at.isoformat()
                    if snapshot.generated_at
                    else None
                ),
                "source_fingerprint": snapshot.source_fingerprint,
                "history": [
                    {
                        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
                        "coverage_score": row.coverage_score,
                        "profile_version": row.profile_version,
                        "source_fingerprint": row.source_fingerprint,
                    }
                    for row in history_rows
                ],
            }
        )
        return result

    def _lifecycle(self, handles: list[DarkWebHandle]) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        timeline = []
        starts, ends = [], []
        for handle in handles:
            start = _as_date(handle.registration_date or handle.first_seen)
            end = _as_date(handle.last_seen)
            if start:
                starts.append(start)
            if end:
                ends.append(end)
            timeline.append(
                {
                    "handle": handle.handle,
                    "marketplace": handle.platform,
                    "status": handle.status,
                    "first_seen": _iso(start),
                    "last_seen": _iso(end),
                    "active_window_days": (
                        max(0, (end - start).days) if start and end else None
                    ),
                }
            )

        first = min(starts) if starts else None
        last = max(ends) if ends else None
        status_counts = _counter_dict(handle.status for handle in handles)
        overlaps = 0
        gaps = []
        ordered = sorted(
            [( _as_date(h.registration_date or h.first_seen), _as_date(h.last_seen)) for h in handles],
            key=lambda pair: pair[0] or date.max,
        )
        for index, (start_a, end_a) in enumerate(ordered):
            if not start_a or not end_a:
                continue
            for start_b, end_b in ordered[index + 1:]:
                if not start_b or not end_b:
                    continue
                if start_b <= end_a and end_b >= start_a:
                    overlaps += 1
                elif start_b > end_a:
                    gaps.append((start_b - end_a).days)

        return {
            "available": bool(handles),
            "first_observed": _iso(first),
            "last_observed": _iso(last),
            "account_age_days": max(0, (today - first).days) if first else None,
            "observed_span_days": max(0, (last - first).days) if first and last else None,
            "days_since_last_seen": (
                (today - last).days if last and last <= today else None
            ),
            "future_dated_handle_count": sum(
                1 for handle in handles
                if _as_date(handle.last_seen) and _as_date(handle.last_seen) > today
            ),
            "handle_timeline": timeline,
            "status_distribution": status_counts,
            "overlapping_handle_windows": overlaps,
            "inter_handle_gap_days": gaps,
            "has_post_timestamps": False,
        }

    def _operational(
        self,
        handles: list[DarkWebHandle],
        wallets: list[Wallet],
        pgp_keys: dict,
        external_pgp_links: list,
        external_wallet_rows: list,
    ) -> Dict[str, Any]:
        marketplace_counts = Counter(
            handle.platform for handle in handles if handle.platform
        )
        wallet_handles: Dict[str, set[str]] = {}
        for wallet in wallets:
            if wallet.address and wallet.associated_handle:
                wallet_handles.setdefault(wallet.address, set()).add(wallet.associated_handle)
        within_reuse = sum(1 for values in wallet_handles.values() if len(values) > 1)
        external_wallet_addresses = {
            row.address for row in external_wallet_rows if row.address
        }
        return {
            "available": bool(handles or wallets or pgp_keys),
            "marketplace_count": len(marketplace_counts),
            "marketplaces": [
                {"name": name, "handle_count": count}
                for name, count in sorted(marketplace_counts.items())
            ],
            "wallet_count": len(wallets),
            "unique_wallet_count": len({w.address for w in wallets if w.address}),
            "within_actor_wallet_reuse_count": within_reuse,
            "cross_actor_shared_wallet_count": len(external_wallet_addresses),
            "pgp_key_count": len(pgp_keys),
            "pgp_reuse_across_other_handles_count": len(
                {row[0] for row in external_pgp_links}
            ),
        }

    def _interaction(
        self,
        actor: Actor,
        handle_ids: list[int],
        trust_links: list[TrustLink],
    ) -> Dict[str, Any]:
        own_ids = set(handle_ids)
        outgoing = [link for link in trust_links if link.source_handle_id in own_ids]
        incoming = [link for link in trust_links if link.target_handle_id in own_ids]
        counterparties = set()
        for link in outgoing:
            if link.target_handle_id not in own_ids:
                counterparties.add(link.target_handle_id)
        for link in incoming:
            if link.source_handle_id not in own_ids:
                counterparties.add(link.source_handle_id)
        confidences = [float(link.confidence) for link in trust_links if link.confidence is not None]
        return {
            "available": bool(trust_links),
            "trust_link_count": len(trust_links),
            "outgoing_count": len(outgoing),
            "incoming_count": len(incoming),
            "distinct_counterparty_handles": len(counterparties),
            "relationship_types": _counter_dict(link.relationship_type for link in trust_links),
            "average_confidence": (
                round(sum(confidences) / len(confidences), 4) if confidences else None
            ),
            "scope_note": "Counts are based on recorded trust-link edges; they do not measure all communications or real-world collaboration.",
        }

    def _infrastructure(self, observations: list[Observation]) -> Dict[str, Any]:
        timestamps = [o.timestamp for o in observations if o.timestamp]
        last = max(timestamps) if timestamps else None
        return {
            "available": bool(observations),
            "observation_count": len(observations),
            "indicator_types": _counter_dict(o.indicator_type for o in observations),
            "sources": _counter_dict(o.source for o in observations),
            "last_observed": last.isoformat() if last else None,
            "mean_observation_confidence": (
                round(
                    sum(float(o.confidence) for o in observations if o.confidence is not None)
                    / len([o for o in observations if o.confidence is not None]),
                    4,
                )
                if any(o.confidence is not None for o in observations)
                else None
            ),
        }

    def _cross_handle_consistency(self, handles: list[str]) -> Dict[str, Any]:
        if len(handles) < 2:
            return {
                "available": False,
                "mean_similarity": None,
                "comparisons": 0,
                "engine_status": nlp_service.engine_status,
                "fallback_used": nlp_service.engine is None,
            }
        scores = []
        fallback_used = False
        for index, handle_a in enumerate(handles):
            for handle_b in handles[index + 1:]:
                result = nlp_service.compare(handle_a, handle_b)
                if result.get("error"):
                    continue
                scores.append(float(result.get("similarity_score", 0.0)))
                fallback_used = fallback_used or bool(result.get("fallback_used"))
        return {
            "available": bool(scores),
            "mean_similarity": round(sum(scores) / len(scores), 4) if scores else None,
            "comparisons": len(scores),
            "engine_status": nlp_service.engine_status,
            "fallback_used": fallback_used,
            "interpretation": "Model similarity across linked handles; not a calibrated probability of common identity.",
        }
