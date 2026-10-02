from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.sql_models import Actor, DarkWebHandle, Wallet, Observation, ScanTarget, InvestigatorFeedback
from app.config import settings
from app.services.observation_scope import build_observation_target_keys
from app.services.nlp_service import nlp_service


# Interpretable investigative weights. These are NOT calibrated probabilities.
SIGNAL_WEIGHTS = {
    "wallet_reuse": 0.25,
    "infrastructure_reuse": 0.20,
    "tls_reuse": 0.15,
    "banner_match": 0.10,
    "descriptor_timing": 0.10,
    "stylometry": 0.20,
}

# Priority is an investigator triage score, not an identity probability.
PRIORITY_WEIGHTS = {
    "risk_severity": 0.30,
    "correlation": 0.25,
    "evidence_confidence": 0.20,
    "recency": 0.15,
    "evidence_coverage": 0.10,
}

RISK_SEVERITY = {
    "critical": 100.0,
    "high": 85.0,
    "medium": 60.0,
    "low": 30.0,
}


class CorrelationService:
    """Evidence fusion and transparent investigator triage scoring."""

    def __init__(self, db: Session):
        self.db = db
        self._actor_target_cache: Dict[str, set[str]] = {}

    def correlate_actor(
        self,
        actor_id: str,
        stylometry_score: Optional[float] = None,
        handle_a: Optional[str] = None,
        handle_b: Optional[str] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
        if not actor:
            raise ValueError(f"Actor {actor_id} not found")

        signals: List[Dict[str, Any]] = []
        source_reliability = self._source_reliability(actor_id)

        wallet_score = self._wallet_reuse_score(actor_id)
        if wallet_score is not None:
            signals.append(self._signal("wallet_reuse", wallet_score, "Wallet address reuse across correlated handles."))

        infrastructure_result = self._observation_score(
            actor_id,
            ["infrastructure_reuse", "infra_reuse", "infrastructure", "exposed_status_page"],
            source_reliability,
        )
        if infrastructure_result is not None:
            signal = self._signal(
                "infrastructure_reuse",
                infrastructure_result["score"],
                "Infrastructure indicators overlap with known observations.",
            )
            signal["details"] = {"source_reliability": infrastructure_result["source_reliability"]}
            signals.append(signal)

        tls_result = self._observation_score(
            actor_id,
            ["ssl_cert_reuse", "tls_reuse", "tls", "certificate"],
            source_reliability,
        )
        if tls_result is not None:
            signal = self._signal(
                "tls_reuse",
                tls_result["score"],
                "TLS/certificate indicators show reuse.",
            )
            signal["details"] = {"source_reliability": tls_result["source_reliability"]}
            signals.append(signal)

        banner_result = self._observation_score(
            actor_id,
            ["banner_match", "default_banner", "banner"],
            source_reliability,
        )
        if banner_result is not None:
            signal = self._signal(
                "banner_match",
                banner_result["score"],
                "Service/banner characteristics overlap.",
            )
            signal["details"] = {"source_reliability": banner_result["source_reliability"]}
            signals.append(signal)

        timing_result = self._observation_score(
            actor_id,
            ["descriptor_timing", "timing", "descriptor"],
            source_reliability,
        )
        if timing_result is not None:
            signal = self._signal(
                "descriptor_timing",
                timing_result["score"],
                "Descriptor timing observations overlap.",
            )
            signal["details"] = {"source_reliability": timing_result["source_reliability"]}
            signals.append(signal)

        nlp_result = None
        contradiction = None
        if handle_a and handle_b:
            nlp_result = nlp_service.compare(handle_a=handle_a, handle_b=handle_b)
            if nlp_result.get("error"):
                raise ValueError(nlp_result["error"])
            stylometry_score = nlp_result.get("similarity_score", 0.0)
            contradiction = nlp_service.check_contradiction(handle_a, handle_b)

        if stylometry_score is not None:
            stylometry_score = self._clamp(stylometry_score)
            signal = self._signal("stylometry", stylometry_score, "Authorship/stylometric similarity from the DeCypher NLP engine.")
            if nlp_result:
                signal["details"] = {
                    "handle_a": handle_a,
                    "handle_b": handle_b,
                    "is_same_author": nlp_result.get("is_same_author", False),
                    "threshold_used": nlp_result.get("threshold_used"),
                    "shared_markers": nlp_result.get("shared_markers", []),
                    "domain_routing": nlp_result.get("domain_routing", {}),
                    "contradiction": contradiction,
                }
            signals.append(signal)

        overall_confidence = self._weighted_score(signals)

        # Human investigator feedback is a bounded triage adjustment to the
        # persisted confidence score. Keep it separate from the evidence
        # signal weights so repeated recalculation remains deterministic.
        feedback_adjustment = self._feedback_confidence_adjustment(actor.actor_id)
        overall_confidence = self._clamp(
            overall_confidence + feedback_adjustment["confidence_delta"]
        )

        if contradiction and contradiction.get("contradiction_flag"):
            # De-confliction is a negative investigative signal, not another positive weight.
            overall_confidence = self._clamp(overall_confidence - 0.15)
        risk_level = self._risk_level(overall_confidence, actor.risk_category)
        priority = self.calculate_priority(actor, overall_confidence, signals)

        # Persist the current triage value so dashboard ordering and actor
        # pages remain consistent. This is a derived score, not ground truth.
        # Persist the live backend-derived attribution confidence and triage priority.
        # The frontend should consume these stored values rather than a static seed default.
        if persist:
            actor.confidence_score = round(overall_confidence, 4)
            actor.priority_score = priority["score"]
            self.db.commit()

        return {
            "candidate_actor": actor.actor_id,
            "primary_handle": actor.primary_handle,
            "overall_confidence": round(overall_confidence, 4),
            "risk_level": risk_level,
            "signals": signals,
            "signal_count": len(signals),
            "available_weight": round(sum(SIGNAL_WEIGHTS.get(s["type"], 0.0) for s in signals), 4),
            "interpretation": self._interpretation(overall_confidence, len(signals)),
            "deconfliction": contradiction,
            "priority": priority,
            "counterfactual": self._counterfactual_analysis(signals),
            "source_reliability": source_reliability,
        }

    def calculate_priority(self, actor: Actor, correlation_score: float, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        risk = self._risk_severity(actor.risk_category)
        evidence_confidence = self._evidence_confidence(actor.actor_id, signals)
        recency = self._recency_score(actor.actor_id)
        coverage = self._coverage_score(signals)
        feedback = self._feedback_adjustment(actor.actor_id)

        components = {
            "risk_severity": round(risk, 2),
            "correlation": round(self._clamp(correlation_score) * 100.0, 2),
            "evidence_confidence": round(evidence_confidence, 2),
            "recency": round(recency, 2),
            "evidence_coverage": round(coverage, 2),
        }
        base_score = round(sum(components[k] * w for k, w in PRIORITY_WEIGHTS.items()))
        score = int(max(0, min(100, base_score + feedback["priority_delta"])))
        return {
            "score": score,
            "base_score": int(max(0, min(100, base_score))),
            "investigator_feedback": feedback,
            "level": self._priority_level(score),
            "components": components,
            "weights": {k: round(v, 2) for k, v in PRIORITY_WEIGHTS.items()},
        }

    def correlate_all(self, stylometry_score: Optional[float] = None) -> List[Dict[str, Any]]:
        actors = self.db.query(Actor).all()
        results = []
        for actor in actors:
            result = self.correlate_actor(
                actor.actor_id,
                stylometry_score=stylometry_score,
                persist=False,
            )
            # persist=False is a pure calculation mode; update the actor here
            # explicitly so bulk correlation performs one transaction.
            actor.confidence_score = result["overall_confidence"]
            actor.priority_score = result["priority"]["score"]
            results.append(result)
        self.db.commit()
        results.sort(
            key=lambda item: (item["priority"]["score"], item["overall_confidence"]),
            reverse=True,
        )
        return results

    def _actor_observation_target_keys(self, actor: Actor) -> set[str]:
        cached = self._actor_target_cache.get(actor.actor_id)
        if cached is not None:
            return cached

        handles = self.db.query(DarkWebHandle).filter(
            DarkWebHandle.actor_id == actor.actor_id
        ).all()
        scan_targets = (
            self.db.query(ScanTarget)
            .filter(ScanTarget.actor_id == actor.actor_id)
            .all()
        )
        targets = build_observation_target_keys(
            actor.actor_id,
            actor.primary_handle,
            handles,
            scan_targets,
        )
        self._actor_target_cache[actor.actor_id] = targets
        return targets

    def _actor_observations(
        self,
        actor: Actor,
        indicator_types: Optional[List[str]] = None,
    ) -> List[Observation]:
        targets = self._actor_observation_target_keys(actor)
        if not targets:
            return []

        query = self.db.query(Observation).filter(
            func.lower(Observation.target).in_(targets),
            Observation.detected.is_(True),
        )
        # Startup filler observations are for the controlled demo UI only.
        # They must not silently become attribution evidence.
        if settings.CORRELATION_EXCLUDE_SYNTHETIC_DEMO_EVIDENCE:
            query = query.filter(
                func.lower(Observation.source) != "synthetic_investigation_evidence"
            )
        if indicator_types:
            query = query.filter(
                Observation.indicator_type.in_(indicator_types)
            )
        return query.all()

    def _wallet_reuse_score(self, actor_id: str) -> Optional[float]:
        wallets = self.db.query(Wallet).filter(Wallet.actor_id == actor_id).all()
        if not wallets:
            return None

        addresses = {wallet.address for wallet in wallets if wallet.address}
        if not addresses:
            return None

        related_wallets = (
            self.db.query(Wallet)
            .filter(Wallet.address.in_(addresses))
            .all()
        )
        handles_by_address: Dict[str, set[str]] = {}
        for wallet in related_wallets:
            if wallet.address and wallet.associated_handle:
                handles_by_address.setdefault(wallet.address, set()).add(wallet.associated_handle)

        reuse_scores = []
        for wallet in wallets:
            handle_count = len(handles_by_address.get(wallet.address, set()))
            if handle_count >= 2:
                reuse_scores.append(0.95)
            elif handle_count == 1:
                reuse_scores.append(0.60)

        return self._clamp(max(reuse_scores)) if reuse_scores else None

    def _observation_score(
        self,
        actor_id: str,
        indicator_types: List[str],
        source_reliability: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
        if not actor:
            return None

        matching = self._actor_observations(actor, indicator_types)
        if not matching:
            return None

        reliability = source_reliability or self._source_reliability(actor_id)
        source_details: Dict[str, Dict[str, Any]] = {}
        candidates = []
        for observation in matching:
            source = (observation.source or "unknown").strip() or "unknown"
            raw_confidence = self._clamp(
                observation.confidence
                if observation.confidence is not None
                else 1.0
            )
            metadata = reliability.get(
                source,
                self._default_source_reliability(source),
            )
            adjusted_confidence = self._clamp(
                raw_confidence * metadata["multiplier"]
            )
            candidates.append(adjusted_confidence)
            source_details[source] = metadata

        return {
            "score": max(candidates) if candidates else None,
            "source_reliability": source_details,
        }

    def _build_actor_target_map(self) -> Dict[str, str]:
        actors = self.db.query(Actor).all()
        handles = self.db.query(DarkWebHandle).all()
        scan_targets = self.db.query(ScanTarget).all()

        handles_by_actor: Dict[str, List[DarkWebHandle]] = {}
        for handle in handles:
            handles_by_actor.setdefault(handle.actor_id or "", []).append(handle)

        scan_targets_by_actor: Dict[str, List[ScanTarget]] = {}
        for target in scan_targets:
            scan_targets_by_actor.setdefault(target.actor_id or "", []).append(target)

        mapping: Dict[str, str] = {}
        for actor in actors:
            keys = build_observation_target_keys(
                actor.actor_id,
                actor.primary_handle,
                handles_by_actor.get(actor.actor_id, []),
                scan_targets_by_actor.get(actor.actor_id, []),
            )
            for key in keys:
                mapping[key.lower()] = actor.actor_id
        return mapping

    @staticmethod
    def _default_source_reliability(source: str) -> Dict[str, Any]:
        return {
            "source": source,
            "prior": 0.50,
            "posterior": 0.50,
            "review_count": 0,
            "confirmed_reviews": 0,
            "false_positive_reviews": 0,
            "review_coverage": 0.0,
            "multiplier": 1.0,
            "basis": "neutral_prior",
        }

    def _source_reliability(self, actor_id: str) -> Dict[str, Dict[str, Any]]:
        """Estimate source reliability from reviewed actors excluding the target actor.

        This is a leave-one-actor-out, review-conditioned reliability estimate.
        It is not a causal source-quality measurement and should not be treated
        as ground truth.
        """
        actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
        actor_sources = {
            (observation.source or "unknown").strip() or "unknown"
            for observation in self._actor_observations(actor)
        } if actor else set()

        target_map = self._build_actor_target_map()
        observations = self.db.query(
            Observation.source,
            Observation.target,
            Observation.detected,
        ).filter(
            Observation.detected.is_(True),
        ).all()

        if settings.CORRELATION_EXCLUDE_SYNTHETIC_DEMO_EVIDENCE:
            observations = [
                row for row in observations
                if (row[0] or "").strip().lower()
                != "synthetic_investigation_evidence"
            ]

        source_actors: Dict[str, set[str]] = {}
        target_actor_ids_by_source: Dict[str, set[str]] = {}
        for source, target, detected in observations:
            if not detected:
                continue
            normalized_source = (source or "unknown").strip() or "unknown"
            linked_actor = target_map.get((target or "").lower())
            if not linked_actor or linked_actor == actor_id:
                continue
            source_actors.setdefault(normalized_source, set()).add(linked_actor)

        feedback_records = (
            self.db.query(InvestigatorFeedback)
            .order_by(
                InvestigatorFeedback.timestamp.desc(),
                InvestigatorFeedback.id.desc(),
            )
            .all()
        )
        latest_review_by_actor: Dict[str, InvestigatorFeedback] = {}
        for record in feedback_records:
            if record.actor_id == actor_id:
                continue
            if record.actor_id in latest_review_by_actor:
                continue
            verdict = (record.verdict or "").lower()
            if "confirm" in verdict:
                latest_review_by_actor[record.actor_id] = record
            elif any(term in verdict for term in ("false", "reject", "dismiss")):
                latest_review_by_actor[record.actor_id] = record

        result: Dict[str, Dict[str, Any]] = {}
        for source, actor_ids in source_actors.items():
            if actor_sources and source not in actor_sources:
                continue
            confirmed = 0
            false_positive = 0
            for linked_actor in actor_ids:
                review = latest_review_by_actor.get(linked_actor)
                if not review:
                    continue
                verdict = (review.verdict or "").lower()
                if "confirm" in verdict:
                    confirmed += 1
                elif any(term in verdict for term in ("false", "reject", "dismiss")):
                    false_positive += 1

            review_count = confirmed + false_positive
            prior = 0.50
            prior_strength = 4.0
            posterior = (
                (prior_strength * prior + confirmed)
                / (prior_strength + review_count)
                if review_count
                else prior
            )
            posterior = max(0.25, min(0.90, posterior))
            coverage = review_count / (review_count + prior_strength)
            multiplier = self._clamp(0.5 + posterior)
            multiplier = max(0.75, min(1.20, multiplier))

            result[source] = {
                "source": source,
                "prior": prior,
                "posterior": round(posterior, 4),
                "review_count": review_count,
                "confirmed_reviews": confirmed,
                "false_positive_reviews": false_positive,
                "review_coverage": round(coverage, 4),
                "multiplier": round(multiplier, 4),
                "basis": "leave_one_actor_out_review_rate",
            }

        return result

    def _counterfactual_analysis(
        self,
        signals: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Measure score sensitivity by removing one available signal at a time."""
        baseline = self._weighted_score(signals)
        scenarios = []
        for signal in signals:
            remaining = [
                other
                for other in signals
                if other["type"] != signal["type"]
            ]
            without = self._weighted_score(remaining)
            delta = baseline - without
            scenarios.append(
                {
                    "removed_signal": signal["type"],
                    "baseline_score": round(baseline, 4),
                    "without_score": round(without, 4),
                    "delta": round(delta, 4),
                    "absolute_impact": round(abs(delta), 4),
                    "remaining_signal_count": len(remaining),
                    "remaining_weight": round(
                        sum(SIGNAL_WEIGHTS.get(item["type"], 0.0) for item in remaining),
                        4,
                    ),
                    "interpretation": (
                        "Removing this signal lowers the evidence score."
                        if delta > 0
                        else "Removing this signal raises the evidence score."
                        if delta < 0
                        else "Removing this signal leaves the evidence score unchanged."
                    ),
                }
            )

        scenarios.sort(key=lambda item: item["absolute_impact"], reverse=True)
        return {
            "available": bool(signals),
            "baseline_evidence_score": round(baseline, 4),
            "scenarios": scenarios,
            "note": (
                "Leave-one-signal-out sensitivity analysis. The delta describes "
                "score sensitivity to the model's current weighted evidence set; "
                "it is not a causal effect or proof that a signal caused the score."
            ),
        }

    def _evidence_confidence(self, actor_id: str, signals: List[Dict[str, Any]]) -> float:
        if not signals:
            actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
            if not actor:
                return 0.0
            observations = self._actor_observations(actor)
            return round(
                max(
                    (
                        self._clamp(observation.confidence or 1.0)
                        for observation in observations
                    ),
                    default=0.0,
                )
                * 100,
                2,
            )
        weighted = sum(s["confidence"] * SIGNAL_WEIGHTS[s["type"]] for s in signals)
        weight = sum(SIGNAL_WEIGHTS[s["type"]] for s in signals)
        return round((weighted / weight) * 100 if weight else 0.0, 2)

    def _recency_score(self, actor_id: str) -> float:
        dates = []
        handles = self.db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor_id).all()
        dates.extend(h.last_seen for h in handles if h.last_seen)
        actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
        if actor:
            dates.extend(
                o.timestamp
                for o in self._actor_observations(actor)
                if o.timestamp
            )
        if not dates:
            return 20.0
        latest = max(dates)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - latest).total_seconds() / 86400)
        if age_days <= 7: return 100.0
        if age_days <= 30: return 80.0
        if age_days <= 90: return 60.0
        if age_days <= 180: return 40.0
        return 20.0

    def _feedback_confidence_adjustment(self, actor_id: str) -> Dict[str, Any]:
        """Apply the latest human verdict as a bounded confidence adjustment."""
        latest = (
            self.db.query(InvestigatorFeedback)
            .filter(InvestigatorFeedback.actor_id == actor_id)
            .order_by(InvestigatorFeedback.timestamp.desc(), InvestigatorFeedback.id.desc())
            .first()
        )
        if not latest:
            return {"confidence_delta": 0.0, "latest_verdict": None}

        verdict = (latest.verdict or "").lower()
        delta = 0.0
        if "confirm" in verdict:
            delta += 0.05
        elif "false" in verdict or "reject" in verdict or "dismiss" in verdict:
            delta -= 0.15

        return {
            "confidence_delta": delta,
            "latest_verdict": latest.verdict,
        }

    def _feedback_adjustment(self, actor_id: str) -> Dict[str, Any]:
        """Keep the latest human verdict as a separate triage adjustment."""
        latest = (
            self.db.query(InvestigatorFeedback)
            .filter(InvestigatorFeedback.actor_id == actor_id)
            .order_by(InvestigatorFeedback.timestamp.desc(), InvestigatorFeedback.id.desc())
            .first()
        )
        if not latest:
            return {"priority_delta": 0, "latest_verdict": None, "investigator_id": None}

        verdict = (latest.verdict or "").lower()
        delta = 0
        if "confirm" in verdict:
            delta += 5
        elif "false" in verdict or "reject" in verdict or "dismiss" in verdict:
            delta -= 15

        if "high" in verdict and "risk" in verdict:
            delta += 10
        elif "low" in verdict and "risk" in verdict:
            delta -= 10

        return {
            "priority_delta": delta,
            "latest_verdict": latest.verdict,
            "investigator_id": latest.investigator_id,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
        }

    @staticmethod
    def _coverage_score(signals: List[Dict[str, Any]]) -> float:
        return round(sum(SIGNAL_WEIGHTS.get(s["type"], 0.0) for s in signals) * 100.0, 2)

    @staticmethod
    def _risk_severity(category: Optional[str]) -> float:
        if not category:
            return 10.0
        category = category.strip().lower()
        if category in RISK_SEVERITY:
            return RISK_SEVERITY[category]
        if any(term in category for term in ("critical", "ransomware", "exploit", "malware", "hacking")):
            return 85.0
        return 60.0

    @staticmethod
    def _priority_level(score: int) -> str:
        if score >= 85: return "critical"
        if score >= 70: return "high"
        if score >= 50: return "medium"
        return "low"

    @staticmethod
    def _weighted_score(signals: List[Dict[str, Any]]) -> float:
        if not signals: return 0.0
        numerator = sum(s["confidence"] * SIGNAL_WEIGHTS.get(s["type"], 0.0) for s in signals)
        denominator = sum(SIGNAL_WEIGHTS.get(s["type"], 0.0) for s in signals)
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _signal(signal_type: str, confidence: float, description: str) -> Dict[str, Any]:
        return {"type": signal_type, "confidence": round(CorrelationService._clamp(confidence), 4), "description": description, "weight": SIGNAL_WEIGHTS.get(signal_type, 0.0)}

    @staticmethod
    def _risk_level(confidence: float, existing_category: Optional[str]) -> str:
        if confidence >= 0.80: return "high"
        if confidence >= 0.55: return "medium"
        if existing_category and existing_category.lower() in {"high", "critical"}: return "high"
        if existing_category and existing_category.lower() == "medium": return "medium"
        return "low"

    @staticmethod
    def _interpretation(confidence: float, signal_count: int) -> str:
        if signal_count == 0: return "Insufficient independent correlation evidence."
        if confidence >= 0.80: return "Strong candidate association based on the available independent signals."
        if confidence >= 0.55: return "Moderate candidate association. Additional evidence should be reviewed."
        return "Weak candidate association based on the currently available evidence."

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
