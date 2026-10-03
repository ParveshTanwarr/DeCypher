"""Deterministic graph-structure anomaly analysis for investigator review."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.sql_models import (
    Actor,
    DarkWebHandle,
    Observation,
    ScanTarget,
    TrustLink,
    Wallet,
)
from app.services.observation_scope import build_observation_target_keys


FEATURE_WEIGHTS = {
    "cross_actor_wallet_reuse": 0.25,
    "shared_pgp_reuse": 0.20,
    "trust_degree": 0.15,
    "external_infrastructure_reuse": 0.15,
    "marketplace_switches": 0.10,
    "temporal_handle_overlap": 0.10,
    "observation_source_diversity": 0.05,
}


def _percentile(values: list[float], value: float) -> float:
    if len(values) <= 1:
        return 50.0
    ordered = sorted(values)
    rank = sum(1 for item in ordered if item <= value) - 1
    return round(100.0 * max(0, rank) / (len(ordered) - 1), 2)


def _tail_score(percentile: float) -> float:
    if percentile <= 80.0:
        return 0.0
    return round(((percentile - 80.0) / 20.0) * 100.0, 2)


def _overlap_count(handles: list[DarkWebHandle]) -> int:
    windows: list[tuple[Any, Any]] = []
    for handle in handles:
        if handle.first_seen and handle.last_seen:
            windows.append((handle.first_seen, handle.last_seen))
    total = 0
    for index, first in enumerate(windows):
        for second in windows[index + 1 :]:
            if first[0] <= second[1] and second[0] <= first[1]:
                total += 1
    return total


def _build_population(db: Session) -> dict[str, dict[str, float]]:
    actors = [row[0] for row in db.query(Actor.actor_id).order_by(Actor.actor_id.asc()).all()]
    actor_set = set(actors)

    handles = (
        db.query(DarkWebHandle)
        .options(joinedload(DarkWebHandle.pgp_keys))
        .filter(DarkWebHandle.actor_id.in_(actors))
        .all()
    )
    handle_by_id = {handle.id: handle for handle in handles}
    handles_by_actor: dict[str, list[DarkWebHandle]] = defaultdict(list)
    actors_by_wallet: dict[str, set[str]] = defaultdict(set)
    actors_by_pgp: dict[str, set[str]] = defaultdict(set)
    actors_by_infra: dict[str, set[str]] = defaultdict(set)
    marketplaces_by_actor: dict[str, set[str]] = defaultdict(set)

    for handle in handles:
        actor_id = str(handle.actor_id)
        handles_by_actor[actor_id].append(handle)
        if handle.platform:
            marketplaces_by_actor[actor_id].add(handle.platform)
        for key in handle.pgp_keys:
            if key.fingerprint:
                actors_by_pgp[key.fingerprint].add(actor_id)

    wallets = db.query(Wallet).filter(Wallet.actor_id.in_(actors)).all()
    for wallet in wallets:
        if wallet.address and wallet.actor_id:
            actors_by_wallet[wallet.address].add(str(wallet.actor_id))

    observations = db.query(Observation).all()
    scan_targets = db.query(ScanTarget).filter(ScanTarget.actor_id.in_(actors)).all()
    handles_by_actor: dict[str, list[DarkWebHandle]] = defaultdict(list)
    for handle in handles:
        if handle.actor_id:
            handles_by_actor[str(handle.actor_id)].append(handle)
    scan_targets_by_actor: dict[str, list[ScanTarget]] = defaultdict(list)
    for target in scan_targets:
        if target.actor_id:
            scan_targets_by_actor[str(target.actor_id)].append(target)

    target_to_actor: dict[str, str] = {}
    actor_rows = {str(actor.actor_id): actor for actor in db.query(Actor).filter(Actor.actor_id.in_(actors)).all()}
    for actor_id in actors:
        actor = actor_rows.get(str(actor_id))
        if not actor:
            continue
        target_to_actor.update({
            key.lower(): str(actor_id)
            for key in build_observation_target_keys(
                actor.actor_id,
                actor.primary_handle,
                handles_by_actor.get(str(actor_id), []),
                scan_targets_by_actor.get(str(actor_id), []),
            )
        })
    for observation in observations:
        actor_id = target_to_actor.get((observation.target or "").strip().lower())
        if actor_id and (observation.value or observation.target):
            actors_by_infra[
                (observation.indicator_type, observation.value or observation.target)
            ].add(actor_id)

    counterparties_by_actor: dict[str, set[str]] = defaultdict(set)
    for link in db.query(TrustLink).all():
        source = handle_by_id.get(link.source_handle_id)
        target = handle_by_id.get(link.target_handle_id)
        if not source or not target or not source.actor_id or not target.actor_id:
            continue
        source_actor, target_actor = str(source.actor_id), str(target.actor_id)
        if source_actor == target_actor:
            continue
        counterparties_by_actor[source_actor].add(target_actor)
        counterparties_by_actor[target_actor].add(source_actor)

    source_diversity_by_actor: dict[str, set[str]] = defaultdict(set)
    for observation in observations:
        actor_id = target_to_actor.get((observation.target or "").strip().lower())
        if actor_id and observation.source:
            source_diversity_by_actor[actor_id].add(observation.source)

    population: dict[str, dict[str, float]] = {}
    for actor_id in actors:
        actor_handles = handles_by_actor[actor_id]
        wallet_reuse = sum(
            1 for address, actor_ids in actors_by_wallet.items()
            if actor_id in actor_ids and len(actor_ids) > 1
        )
        pgp_reuse = sum(
            1 for fingerprint, actor_ids in actors_by_pgp.items()
            if actor_id in actor_ids and len(actor_ids) > 1
        )
        infra_reuse = sum(
            1 for _, actor_ids in actors_by_infra.items()
            if actor_id in actor_ids and len(actor_ids) > 1
        )
        population[actor_id] = {
            "cross_actor_wallet_reuse": float(wallet_reuse),
            "shared_pgp_reuse": float(pgp_reuse),
            "trust_degree": float(len(counterparties_by_actor[actor_id])),
            "external_infrastructure_reuse": float(infra_reuse),
            "marketplace_switches": float(max(0, len(marketplaces_by_actor[actor_id]) - 1)),
            "temporal_handle_overlap": float(_overlap_count(actor_handles)),
            "observation_source_diversity": float(len(source_diversity_by_actor[actor_id])),
        }
    return population


class GraphAnomalyService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _score_population(
        population: dict[str, dict[str, float]],
        actor_id: str,
    ) -> dict[str, Any]:
        if actor_id not in population:
            raise ValueError(f"Actor '{actor_id}' not found.")

        features = population[actor_id]
        percentiles = {
            name: _percentile([row[name] for row in population.values()], value)
            for name, value in features.items()
        }
        tail_scores = {
            name: _tail_score(score)
            for name, score in percentiles.items()
        }
        weighted_score = sum(
            tail_scores[name] * FEATURE_WEIGHTS[name]
            for name in FEATURE_WEIGHTS
        )
        weighted_score = round(max(0.0, min(100.0, weighted_score)), 2)

        reasons = []
        for name, score in sorted(
            tail_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            if score >= 50.0:
                reasons.append({
                    "feature": name,
                    "feature_value": features[name],
                    "population_percentile": percentiles[name],
                    "tail_score": score,
                })

        return {
            "actor_id": actor_id,
            "anomaly_score": weighted_score,
            "level": (
                "high_structural_outlier"
                if weighted_score >= 70
                else "elevated_structural_outlier"
                if weighted_score >= 40
                else "no_strong_structural_outlier"
            ),
            "features": features,
            "feature_percentiles": percentiles,
            "feature_tail_scores": tail_scores,
            "contributing_features": reasons,
            "feature_weights": FEATURE_WEIGHTS,
            "methodology": (
                "Deterministic population-relative graph analysis. Features describe "
                "cross-actor reuse, relationship degree, infrastructure reuse, marketplace "
                "switching and temporal overlap. Percentiles are converted into an upper-tail "
                "outlier score. This is an investigator triage signal, not an identity verdict "
                "and not a causal model."
            ),
        }

    def analyze(self, actor_id: str) -> dict[str, Any]:
        return self._score_population(_build_population(self.db), actor_id)

    def analyze_all(self, limit: int = 25) -> dict[str, Any]:
        population = _build_population(self.db)
        results = [
            self._score_population(population, actor_id)
            for actor_id in population
        ]
        results.sort(key=lambda item: item["anomaly_score"], reverse=True)
        return {
            "total_actors": len(results),
            "results": results[:limit],
            "limit": limit,
        }
