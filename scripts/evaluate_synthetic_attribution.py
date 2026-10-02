"""Evaluate the bundled authorship engine against the synthetic ground-truth dataset.

This is an offline validation harness only. It deliberately uses actor_id_ground_truth
from the synthetic dataset as an answer key and never feeds the label into the model.
It must not be described as real-world attribution validation.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.nlp_service import nlp_service  # noqa: E402


def build_pairs(handles: pd.DataFrame, max_pairs: int, seed: int) -> list[tuple[str, str, int]]:
    rng = random.Random(seed)
    rows = handles.dropna(
        subset=["handle_id", "handle_name", "actor_id_ground_truth"]
    ).copy()
    rows["handle_id"] = rows["handle_id"].astype(str)
    rows["handle_name"] = rows["handle_name"].astype(str)
    rows["actor_id_ground_truth"] = rows["actor_id_ground_truth"].astype(str)

    by_actor: dict[str, list[tuple[str, str]]] = {}
    for row in rows.itertuples(index=False):
        by_actor.setdefault(row.actor_id_ground_truth, []).append(
            (row.handle_id, row.handle_name)
        )

    actors_with_pairs = [
        actor_id
        for actor_id, actor_handles in by_actor.items()
        if len(actor_handles) >= 2
    ]
    if not actors_with_pairs:
        return []

    same_pairs: list[tuple[str, str, int]] = []
    for actor_id in actors_with_pairs:
        actor_handles = by_actor[actor_id][:]
        rng.shuffle(actor_handles)
        for index in range(0, len(actor_handles) - 1, 2):
            same_pairs.append(
                (
                    actor_handles[index][1],
                    actor_handles[index + 1][1],
                    1,
                )
            )

    all_handles = [(hid, name, actor) for actor, values in by_actor.items() for hid, name in values]
    cross_pairs: list[tuple[str, str, int]] = []
    for _ in range(max(len(same_pairs), 1)):
        first, second = rng.sample(all_handles, 2)
        if first[2] == second[2]:
            continue
        cross_pairs.append((first[1], second[1], 0))

    rng.shuffle(same_pairs)
    rng.shuffle(cross_pairs)
    half = max_pairs // 2
    pairs = same_pairs[:half] + cross_pairs[: max_pairs - half]
    rng.shuffle(pairs)
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    handles_path = ROOT / "data" / "handles.csv"
    handles = pd.read_csv(handles_path)
    pairs = build_pairs(handles, max_pairs=max(2, args.pairs), seed=args.seed)
    if not pairs:
        raise SystemExit("Could not construct a synthetic evaluation set.")

    y_true: list[int] = []
    y_pred: list[int] = []
    scores: list[float] = []
    fallback_used = False

    for handle_a, handle_b, label in pairs:
        result = nlp_service.compare(handle_a, handle_b)
        y_true.append(label)
        y_pred.append(int(bool(result.get("is_same_author"))))
        scores.append(float(result.get("similarity_score") or 0.0))
        fallback_used = fallback_used or bool(result.get("fallback_used"))

    print("DeCypher synthetic authorship evaluation")
    print("----------------------------------------")
    print(f"engine_status: {nlp_service.engine_status}")
    print(f"fallback_used: {fallback_used}")
    print(f"pairs_evaluated: {len(y_true)}")
    print(f"accuracy: {accuracy_score(y_true, y_pred):.4f}")
    print(f"precision: {precision_score(y_true, y_pred, zero_division=0):.4f}")
    print(f"recall: {recall_score(y_true, y_pred, zero_division=0):.4f}")
    print(f"f1: {f1_score(y_true, y_pred, zero_division=0):.4f}")

    if len(set(y_true)) == 2:
        print(f"roc_auc: {roc_auc_score(y_true, scores):.4f}")
    else:
        print("roc_auc: unavailable (only one class present)")

    print()
    print(
        "Boundary: this benchmark uses only the repository's synthetic ground-truth labels. "
        "It does not establish real-world attribution accuracy and should not be reported as "
        "such."
    )


if __name__ == "__main__":
    main()
