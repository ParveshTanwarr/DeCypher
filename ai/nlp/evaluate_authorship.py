"""Evaluate the bundled DeCypher authorship engine on synthetic handle pairs.

This benchmark uses handles.csv actor_id_ground_truth only as the evaluation label;
the label is never passed to the model. It reports pairwise classification and
ranking metrics from the model similarity probability.

Important methodological boundary:
the repository does not document an independent training/holdout split for the
bundled joblib artifacts. Therefore this is a reproducible dataset benchmark,
not a claim of independent generalization. Use an independently held-out actor
set for a deployment-grade validation study.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "ai" / "nlp" / "models"


def build_pairs(
    handles: pd.DataFrame,
    max_positive: int,
    seed: int,
) -> list[tuple[str, str, int]]:
    """Build a deterministic, balanced positive/hard-negative pair set.

    Positive pairs come from the same ground-truth actor. Negative pairs are
    split between same-marketplace negatives (when marketplace data exists)
    and unconstrained different-actor negatives, making the benchmark harder
    than purely random actor pairs.
    """
    required = {"handle_id", "actor_id_ground_truth"}
    missing = required - set(handles.columns)
    if missing:
        raise ValueError(
            f"handles.csv is missing required columns: {sorted(missing)}"
        )

    rows = handles[
        [c for c in ["handle_id", "actor_id_ground_truth", "marketplace"] if c in handles.columns]
    ].dropna(subset=["handle_id", "actor_id_ground_truth"]).astype(str).drop_duplicates()

    groups = {
        actor: sorted(group["handle_id"].tolist())
        for actor, group in rows.groupby("actor_id_ground_truth")
    }

    positive_pairs: list[tuple[str, str, int]] = []
    for _, handle_ids in sorted(groups.items()):
        for i, left in enumerate(handle_ids):
            for right in handle_ids[i + 1:]:
                positive_pairs.append((left, right, 1))

    rng = random.Random(seed)
    positive_pairs = sorted(positive_pairs, key=lambda pair: (pair[0], pair[1]))
    rng.shuffle(positive_pairs)
    positive_pairs = positive_pairs[:max_positive]

    actors = sorted(groups)
    if len(actors) < 2:
        raise ValueError("At least two ground-truth actors are required.")

    handle_actor = {
        str(row.handle_id): str(row.actor_id_ground_truth)
        for row in rows.itertuples(index=False)
    }

    marketplace_groups: dict[str, list[str]] = {}
    if "marketplace" in rows.columns:
        for row in rows.itertuples(index=False):
            marketplace = str(row.marketplace).strip()
            if marketplace:
                marketplace_groups.setdefault(marketplace, []).append(str(row.handle_id))
        for marketplace in marketplace_groups:
            marketplace_groups[marketplace] = sorted(set(marketplace_groups[marketplace]))

    pair_keys: set[tuple[str, str]] = {
        tuple(sorted((left, right))) for left, right, _ in positive_pairs
    }

    hard_negative_candidates: list[tuple[str, str, int]] = []
    for handles_in_marketplace in sorted(marketplace_groups.values(), key=lambda ids: tuple(ids)):
        for i, left in enumerate(handles_in_marketplace):
            for right in handles_in_marketplace[i + 1:]:
                if handle_actor[left] != handle_actor[right]:
                    key = tuple(sorted((left, right)))
                    if key not in pair_keys:
                        hard_negative_candidates.append((left, right, 0))

    rng.shuffle(hard_negative_candidates)

    hard_target = min(
        len(hard_negative_candidates),
        max_positive // 2,
    )
    negative_pairs = hard_negative_candidates[:hard_target]
    pair_keys.update(tuple(sorted((left, right))) for left, right, _ in negative_pairs)

    while len(negative_pairs) < len(positive_pairs):
        actor_a, actor_b = rng.sample(actors, 2)
        left = rng.choice(groups[actor_a])
        right = rng.choice(groups[actor_b])
        key = tuple(sorted((left, right)))
        if key in pair_keys:
            continue
        negative_pairs.append((left, right, 0))
        pair_keys.add(key)

    return positive_pairs + negative_pairs


def aggregate_posts(posts: pd.DataFrame) -> dict[str, str]:
    """Concatenate all posts for each handle once to avoid repeated scans."""
    required = {"handle_id", "text"}
    missing = required - set(posts.columns)
    if missing:
        raise ValueError(f"posts.csv is missing required columns: {sorted(missing)}")

    frame = posts[["handle_id", "text"]].dropna().copy()
    frame["handle_id"] = frame["handle_id"].astype(str)
    frame["text"] = frame["text"].astype(str)
    return frame.groupby("handle_id", sort=False)["text"].agg(" ".join).to_dict()


def _score_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    series = pd.Series(values, dtype=float)
    return {
        "min": round(float(series.min()), 4),
        "max": round(float(series.max()), 4),
        "mean": round(float(series.mean()), 4),
        "median": round(float(series.median()), 4),
    }


def evaluate(data_dir: Path, model_dir: Path, max_positive: int, seed: int) -> dict[str, Any]:
    """Run the authorship benchmark and return a JSON-serializable report."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from ai.nlp.compare_handles import DeCypherAuthorshipEngine

    handles = pd.read_csv(data_dir / "handles.csv")
    posts = pd.read_csv(data_dir / "posts.csv")
    pairs = build_pairs(handles, max_positive=max_positive, seed=seed)
    texts = aggregate_posts(posts)
    engine = DeCypherAuthorshipEngine(model_dir=str(model_dir))

    labels: list[int] = []
    predictions: list[int] = []
    scores: list[float] = []
    thresholds: list[float] = []
    evaluated_pairs: list[dict[str, Any]] = []
    skipped = 0

    for handle_a, handle_b, label in pairs:
        text_a = texts.get(handle_a, "").strip()
        text_b = texts.get(handle_b, "").strip()
        if not text_a or not text_b:
            skipped += 1
            continue

        result = engine.compare_texts(text_a, text_b)
        score = float(result["same_author_probability"]) / 100.0
        predicted = int(bool(result["is_likely_match"]))
        threshold = float(result["threshold_used"])

        labels.append(label)
        predictions.append(predicted)
        scores.append(score)
        thresholds.append(threshold)
        evaluated_pairs.append(
            {
                "handle_a": handle_a,
                "handle_b": handle_b,
                "ground_truth_same_actor": bool(label),
                "predicted_same_actor": bool(predicted),
                "score": round(score, 4),
                "threshold": round(threshold, 4),
            }
        )

    if not labels:
        raise ValueError("No evaluable handle pairs had usable post text.")

    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()

    positive_scores = [score for label, score in zip(labels, scores) if label == 1]
    negative_scores = [score for label, score in zip(labels, scores) if label == 0]

    metrics = {
        "accuracy": round(accuracy_score(labels, predictions), 4),
        "precision": round(precision_score(labels, predictions, zero_division=0), 4),
        "recall": round(recall_score(labels, predictions, zero_division=0), 4),
        "f1": round(f1_score(labels, predictions, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(labels, scores), 4)
        if len(set(labels)) == 2
        else None,
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
        "mean_threshold": round(sum(thresholds) / len(thresholds), 4),
        "positive_score_distribution": _score_summary(positive_scores),
        "negative_score_distribution": _score_summary(negative_scores),
    }

    return {
        "benchmark": {
            "name": "DeCypher synthetic authorship pair benchmark",
            "seed": seed,
            "requested_positive_pairs": max_positive,
            "requested_total_pairs": max_positive * 2,
            "evaluated_pairs": len(labels),
            "skipped_pairs": skipped,
            "positive_pairs": sum(labels),
            "negative_pairs": len(labels) - sum(labels),
            "hard_negative_sampling": bool("marketplace" in handles.columns),
        },
        "methodology": {
            "pair_label": "same actor when actor_id_ground_truth matches",
            "model_input": "aggregated post text by handle_id",
            "ground_truth_used_as_model_input": False,
            "negative_sampling": (
                "same-marketplace different-actor negatives where marketplace data exists, "
                "plus unconstrained different-actor negatives"
            ),
            "independent_holdout_confirmed": False,
            "note": (
                "Metrics are a reproducible benchmark on the bundled synthetic dataset. "
                "The repository does not document an independent holdout set for the bundled "
                "model artifacts, so these metrics must not be presented as independent "
                "generalization performance."
            ),
        },
        "metrics": metrics,
        "pair_examples": evaluated_pairs[:25],
    }


def markdown_report(report: dict[str, Any]) -> str:
    benchmark = report["benchmark"]
    method = report["methodology"]
    metrics = report["metrics"]
    roc_auc = (
        f'{metrics["roc_auc"]:.4f}'
        if metrics["roc_auc"] is not None
        else "N/A"
    )

    lines = [
        "# DeCypher Authorship Evaluation",
        "",
        "## Benchmark",
        "",
        f'- Requested positive pairs: {benchmark["requested_positive_pairs"]}',
        f'- Evaluated pairs: {benchmark["evaluated_pairs"]}',
        f'- Skipped pairs: {benchmark["skipped_pairs"]}',
        f'- Positive pairs: {benchmark["positive_pairs"]}',
        f'- Negative pairs: {benchmark["negative_pairs"]}',
        f'- Hard-negative sampling enabled: {benchmark["hard_negative_sampling"]}',
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f'| Accuracy | {metrics["accuracy"]:.4f} |',
        f'| Precision | {metrics["precision"]:.4f} |',
        f'| Recall | {metrics["recall"]:.4f} |',
        f'| F1 | {metrics["f1"]:.4f} |',
        f"| ROC-AUC | {roc_auc} |",
        f'| False positives | {metrics["false_positive"]} |',
        f'| False negatives | {metrics["false_negative"]} |',
        f'| Mean decision threshold | {metrics["mean_threshold"]:.4f} |',
        "",
        "## Score distributions",
        "",
        "| Population | Min | Median | Mean | Max |",
        "|---|---:|---:|---:|---:|",
        f'| Same-actor | {metrics["positive_score_distribution"].get("min", 0):.4f} | {metrics["positive_score_distribution"].get("median", 0):.4f} | {metrics["positive_score_distribution"].get("mean", 0):.4f} | {metrics["positive_score_distribution"].get("max", 0):.4f} |',
        f'| Different-actor | {metrics["negative_score_distribution"].get("min", 0):.4f} | {metrics["negative_score_distribution"].get("median", 0):.4f} | {metrics["negative_score_distribution"].get("mean", 0):.4f} | {metrics["negative_score_distribution"].get("max", 0):.4f} |',
        "",
        "## Methodological note",
        "",
        method["note"],
        "",
        "The actor_id_ground_truth field is used only to label evaluation pairs and is never passed to the authorship engine.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument(
        "--max-positive",
        type=int,
        default=200,
        help="Maximum number of positive same-actor pairs; negatives are balanced to match.",
    )
    parser.add_argument("--seed", type=int, default=26151)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    if args.max_positive < 1:
        parser.error("--max-positive must be at least 1")

    report = evaluate(
        data_dir=args.data_dir,
        model_dir=args.model_dir,
        max_positive=args.max_positive,
        seed=args.seed,
    )
    print(json.dumps(report, indent=2))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(
            markdown_report(report),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
