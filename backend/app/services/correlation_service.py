from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.sql_models import (
    Actor,
    DarkWebHandle,
    Wallet,
    Observation,
)
from app.services.nlp_service import nlp_service


# Interpretable investigative weights.
# These are NOT calibrated probabilities of identity.
SIGNAL_WEIGHTS = {
    "wallet_reuse": 0.25,
    "infrastructure_reuse": 0.20,
    "tls_reuse": 0.15,
    "banner_match": 0.10,
    "descriptor_timing": 0.10,
    "stylometry": 0.20,
}


class CorrelationService:
    """
    Evidence-fusion service for candidate actor association.

    Combines independent investigative signals into an interpretable
    correlation score.

    Important:
    - The score is investigative support, not proof of identity.
    - Missing signals are excluded from the denominator.
    - Existing actor_id relationships are not treated as independent
      evidence by themselves.
    - Stylometry uses the existing DeCypher authorship engine.
    """

    def __init__(self, db: Session):
        self.db = db

    def correlate_actor(
        self,
        actor_id: str,
        stylometry_score: Optional[float] = None,
        handle_a: Optional[str] = None,
        handle_b: Optional[str] = None,
    ) -> Dict[str, Any]:

        actor = (
            self.db.query(Actor)
            .filter(Actor.actor_id == actor_id)
            .first()
        )

        if not actor:
            raise ValueError(f"Actor {actor_id} not found")

        signals: List[Dict[str, Any]] = []

        # ---------------------------------------------------------
        # WALLET REUSE
        # ---------------------------------------------------------

        wallet_score = self._wallet_reuse_score(actor_id)

        if wallet_score is not None:
            signals.append(
                self._signal(
                    "wallet_reuse",
                    wallet_score,
                    "Wallet address reuse across correlated handles.",
                )
            )

        # ---------------------------------------------------------
        # INFRASTRUCTURE REUSE
        # ---------------------------------------------------------

        infrastructure_score = self._observation_score(
            actor_id,
            [
                "infrastructure_reuse",
                "infra_reuse",
                "infrastructure",
            ],
        )

        if infrastructure_score is not None:
            signals.append(
                self._signal(
                    "infrastructure_reuse",
                    infrastructure_score,
                    "Infrastructure indicators overlap with known observations.",
                )
            )

        # ---------------------------------------------------------
        # TLS / CERTIFICATE REUSE
        # ---------------------------------------------------------

        tls_score = self._observation_score(
            actor_id,
            [
                "ssl_cert_reuse",
                "tls_reuse",
                "tls",
                "certificate",
            ],
        )

        if tls_score is not None:
            signals.append(
                self._signal(
                    "tls_reuse",
                    tls_score,
                    "TLS/certificate indicators show reuse.",
                )
            )

        # ---------------------------------------------------------
        # BANNER MATCH
        # ---------------------------------------------------------

        banner_score = self._observation_score(
            actor_id,
            [
                "banner_match",
                "default_banner",
                "banner",
            ],
        )

        if banner_score is not None:
            signals.append(
                self._signal(
                    "banner_match",
                    banner_score,
                    "Service/banner characteristics overlap.",
                )
            )

        # ---------------------------------------------------------
        # DESCRIPTOR / TIMING
        # ---------------------------------------------------------

        timing_score = self._observation_score(
            actor_id,
            [
                "descriptor_timing",
                "timing",
                "descriptor",
            ],
        )

        if timing_score is not None:
            signals.append(
                self._signal(
                    "descriptor_timing",
                    timing_score,
                    "Descriptor timing observations overlap.",
                )
            )

        # ---------------------------------------------------------
        # STYLOMETRY / NLP
        # ---------------------------------------------------------

        nlp_result = None

        if handle_a and handle_b:
            nlp_result = nlp_service.compare(
                handle_a=handle_a,
                handle_b=handle_b,
            )

            if nlp_result.get("error"):
                raise ValueError(nlp_result["error"])

            stylometry_score = nlp_result.get(
                "similarity_score",
                0.0,
            )

        if stylometry_score is not None:
            stylometry_score = self._clamp(
                stylometry_score
            )

            signal = self._signal(
                "stylometry",
                stylometry_score,
                "Authorship/stylometric similarity from the DeCypher NLP engine.",
            )

            if nlp_result:
                signal["details"] = {
                    "handle_a": handle_a,
                    "handle_b": handle_b,
                    "is_same_author": nlp_result.get(
                        "is_same_author",
                        False,
                    ),
                    "threshold_used": nlp_result.get(
                        "threshold_used"
                    ),
                    "shared_markers": nlp_result.get(
                        "shared_markers",
                        [],
                    ),
                    "domain_routing": nlp_result.get(
                        "domain_routing",
                        {},
                    ),
                }

            signals.append(signal)

        # ---------------------------------------------------------
        # FINAL WEIGHTED SCORE
        # ---------------------------------------------------------

        overall_confidence = self._weighted_score(
            signals
        )

        risk_level = self._risk_level(
            overall_confidence,
            actor.risk_category,
        )

        return {
            "candidate_actor": actor.actor_id,
            "primary_handle": actor.primary_handle,
            "overall_confidence": round(
                overall_confidence,
                4,
            ),
            "risk_level": risk_level,
            "signals": signals,
            "signal_count": len(signals),
            "available_weight": round(
                sum(
                    SIGNAL_WEIGHTS.get(
                        signal["type"],
                        0.0,
                    )
                    for signal in signals
                ),
                4,
            ),
            "interpretation": self._interpretation(
                overall_confidence,
                len(signals),
            ),
        }

    def correlate_all(
        self,
        stylometry_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:

        actors = (
            self.db.query(Actor)
            .order_by(
                Actor.priority_score.desc(),
                Actor.actor_id,
            )
            .all()
        )

        results = []

        for actor in actors:
            result = self.correlate_actor(
                actor.actor_id,
                stylometry_score=stylometry_score,
            )

            results.append(result)

        results.sort(
            key=lambda item: item["overall_confidence"],
            reverse=True,
        )

        return results

    # =============================================================
    # WALLET CORRELATION
    # =============================================================

    def _wallet_reuse_score(
        self,
        actor_id: str,
    ) -> Optional[float]:

        wallets = (
            self.db.query(Wallet)
            .filter(
                Wallet.actor_id == actor_id
            )
            .all()
        )

        if not wallets:
            return None

        reuse_scores = []

        for wallet in wallets:

            address = wallet.address

            related_wallets = (
                self.db.query(Wallet)
                .filter(
                    Wallet.address == address
                )
                .all()
            )

            handles = {
                item.associated_handle
                for item in related_wallets
                if item.associated_handle
            }

            if len(handles) >= 2:
                reuse_scores.append(0.95)

            elif len(handles) == 1:
                reuse_scores.append(0.60)

        if not reuse_scores:
            return None

        return self._clamp(
            max(reuse_scores)
        )

    # =============================================================
    # OBSERVATION CORRELATION
    # =============================================================

    def _observation_score(
        self,
        actor_id: str,
        indicator_types: List[str],
    ) -> Optional[float]:

        observations = (
            self.db.query(Observation)
            .filter(
                Observation.indicator_type.in_(
                    indicator_types
                ),
                Observation.detected.is_(True),
            )
            .all()
        )

        if not observations:
            return None

        actor = (
            self.db.query(Actor)
            .filter(
                Actor.actor_id == actor_id
            )
            .first()
        )

        if not actor:
            return None

        handles = {
            handle.handle
            for handle in (
                self.db.query(DarkWebHandle)
                .filter(
                    DarkWebHandle.actor_id == actor_id
                )
                .all()
            )
        }

        targets = {
            actor_id,
            actor.primary_handle,
        }

        targets.update(handles)

        matching = [
            observation
            for observation in observations
            if observation.target in targets
        ]

        if not matching:
            return None

        confidences = [
            self._clamp(
                observation.confidence
                if observation.confidence is not None
                else 1.0
            )
            for observation in matching
        ]

        return max(confidences)

    # =============================================================
    # WEIGHTED FUSION
    # =============================================================

    @staticmethod
    def _weighted_score(
        signals: List[Dict[str, Any]],
    ) -> float:

        if not signals:
            return 0.0

        numerator = 0.0
        denominator = 0.0

        for signal in signals:

            signal_type = signal["type"]

            score = signal["confidence"]

            weight = SIGNAL_WEIGHTS.get(
                signal_type,
                0.0,
            )

            numerator += score * weight
            denominator += weight

        if denominator == 0:
            return 0.0

        return numerator / denominator

    # =============================================================
    # SIGNAL FORMAT
    # =============================================================

    @staticmethod
    def _signal(
        signal_type: str,
        confidence: float,
        description: str,
    ) -> Dict[str, Any]:

        return {
            "type": signal_type,
            "confidence": round(
                CorrelationService._clamp(
                    confidence
                ),
                4,
            ),
            "description": description,
            "weight": SIGNAL_WEIGHTS.get(
                signal_type,
                0.0,
            ),
        }

    # =============================================================
    # RISK LEVEL
    # =============================================================

    @staticmethod
    def _risk_level(
        confidence: float,
        existing_category: Optional[str],
    ) -> str:

        if confidence >= 0.80:
            return "high"

        if confidence >= 0.55:
            return "medium"

        if existing_category:

            category = (
                existing_category.lower()
            )

            if category in {
                "high",
                "critical",
            }:
                return "high"

            if category == "medium":
                return "medium"

        return "low"

    # =============================================================
    # INTERPRETATION
    # =============================================================

    @staticmethod
    def _interpretation(
        confidence: float,
        signal_count: int,
    ) -> str:

        if signal_count == 0:
            return (
                "Insufficient independent correlation evidence."
            )

        if confidence >= 0.80:
            return (
                "Strong candidate association based on "
                "the available independent signals."
            )

        if confidence >= 0.55:
            return (
                "Moderate candidate association. "
                "Additional evidence should be reviewed."
            )

        return (
            "Weak candidate association based on the "
            "currently available evidence."
        )

    # =============================================================
    # SAFETY / NORMALIZATION
    # =============================================================

    @staticmethod
    def _clamp(value: float) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )