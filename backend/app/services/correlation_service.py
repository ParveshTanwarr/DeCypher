from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.sql_models import Actor, DarkWebHandle, Wallet, Observation
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

    def correlate_actor(
        self,
        actor_id: str,
        stylometry_score: Optional[float] = None,
        handle_a: Optional[str] = None,
        handle_b: Optional[str] = None,
    ) -> Dict[str, Any]:
        actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
        if not actor:
            raise ValueError(f"Actor {actor_id} not found")

        signals: List[Dict[str, Any]] = []

        wallet_score = self._wallet_reuse_score(actor_id)
        if wallet_score is not None:
            signals.append(self._signal("wallet_reuse", wallet_score, "Wallet address reuse across correlated handles."))

        infrastructure_score = self._observation_score(actor_id, ["infrastructure_reuse", "infra_reuse", "infrastructure"])
        if infrastructure_score is not None:
            signals.append(self._signal("infrastructure_reuse", infrastructure_score, "Infrastructure indicators overlap with known observations."))

        tls_score = self._observation_score(actor_id, ["ssl_cert_reuse", "tls_reuse", "tls", "certificate"])
        if tls_score is not None:
            signals.append(self._signal("tls_reuse", tls_score, "TLS/certificate indicators show reuse."))

        banner_score = self._observation_score(actor_id, ["banner_match", "default_banner", "banner"])
        if banner_score is not None:
            signals.append(self._signal("banner_match", banner_score, "Service/banner characteristics overlap."))

        timing_score = self._observation_score(actor_id, ["descriptor_timing", "timing", "descriptor"])
        if timing_score is not None:
            signals.append(self._signal("descriptor_timing", timing_score, "Descriptor timing observations overlap."))

        nlp_result = None
        if handle_a and handle_b:
            nlp_result = nlp_service.compare(handle_a=handle_a, handle_b=handle_b)
            if nlp_result.get("error"):
                raise ValueError(nlp_result["error"])
            stylometry_score = nlp_result.get("similarity_score", 0.0)

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
                }
            signals.append(signal)

        overall_confidence = self._weighted_score(signals)
        risk_level = self._risk_level(overall_confidence, actor.risk_category)
        priority = self.calculate_priority(actor, overall_confidence, signals)

        # Persist the current triage value so dashboard ordering and actor
        # pages remain consistent. This is a derived score, not ground truth.
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
            "priority": priority,
        }

    def calculate_priority(self, actor: Actor, correlation_score: float, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        risk = self._risk_severity(actor.risk_category)
        evidence_confidence = self._evidence_confidence(actor.actor_id, signals)
        recency = self._recency_score(actor.actor_id)
        coverage = self._coverage_score(signals)

        components = {
            "risk_severity": round(risk, 2),
            "correlation": round(self._clamp(correlation_score) * 100.0, 2),
            "evidence_confidence": round(evidence_confidence, 2),
            "recency": round(recency, 2),
            "evidence_coverage": round(coverage, 2),
        }
        score = round(sum(components[k] * w for k, w in PRIORITY_WEIGHTS.items()))
        score = int(max(0, min(100, score)))
        return {
            "score": score,
            "level": self._priority_level(score),
            "components": components,
            "weights": {k: round(v, 2) for k, v in PRIORITY_WEIGHTS.items()},
        }

    def correlate_all(self, stylometry_score: Optional[float] = None) -> List[Dict[str, Any]]:
        actors = self.db.query(Actor).all()
        results = []
        for actor in actors:
            results.append(self.correlate_actor(actor.actor_id, stylometry_score=stylometry_score))
        results.sort(key=lambda item: (item["priority"]["score"], item["overall_confidence"]), reverse=True)
        return results

    def _wallet_reuse_score(self, actor_id: str) -> Optional[float]:
        wallets = self.db.query(Wallet).filter(Wallet.actor_id == actor_id).all()
        if not wallets:
            return None
        reuse_scores = []
        for wallet in wallets:
            related_wallets = self.db.query(Wallet).filter(Wallet.address == wallet.address).all()
            handles = {item.associated_handle for item in related_wallets if item.associated_handle}
            if len(handles) >= 2:
                reuse_scores.append(0.95)
            elif len(handles) == 1:
                reuse_scores.append(0.60)
        return self._clamp(max(reuse_scores)) if reuse_scores else None

    def _observation_score(self, actor_id: str, indicator_types: List[str]) -> Optional[float]:
        observations = self.db.query(Observation).filter(Observation.indicator_type.in_(indicator_types), Observation.detected.is_(True)).all()
        if not observations:
            return None
        actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
        if not actor:
            return None
        handles = {h.handle for h in self.db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor_id).all()}
        targets = {actor_id, actor.primary_handle, *handles}
        matching = [o for o in observations if o.target in targets]
        if not matching:
            return None
        return max(self._clamp(o.confidence if o.confidence is not None else 1.0) for o in matching)

    def _evidence_confidence(self, actor_id: str, signals: List[Dict[str, Any]]) -> float:
        if not signals:
            observations = self.db.query(Observation).filter(Observation.target == actor_id, Observation.detected.is_(True)).all()
            return round(max((self._clamp(o.confidence or 1.0) for o in observations), default=0.0) * 100, 2)
        weighted = sum(s["confidence"] * SIGNAL_WEIGHTS[s["type"]] for s in signals)
        weight = sum(SIGNAL_WEIGHTS[s["type"]] for s in signals)
        return round((weighted / weight) * 100 if weight else 0.0, 2)

    def _recency_score(self, actor_id: str) -> float:
        dates = []
        handles = self.db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor_id).all()
        dates.extend(h.last_seen for h in handles if h.last_seen)
        observations = self.db.query(Observation).filter(Observation.detected.is_(True)).all()
        actor = self.db.query(Actor).filter(Actor.actor_id == actor_id).first()
        targets = {actor_id, actor.primary_handle} if actor else {actor_id}
        targets.update(h.handle for h in handles)
        dates.extend(o.timestamp for o in observations if o.target in targets and o.timestamp)
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
