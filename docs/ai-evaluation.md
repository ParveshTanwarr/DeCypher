# AI Authorship Evaluation

DeCypher includes a reproducible benchmark for the bundled authorship engine.

## Run

From the repository root:

python ai/nlp/evaluate_authorship.py --max-positive 200

To save reports:

python ai/nlp/evaluate_authorship.py --max-positive 200 --json-out reports/ai_authorship_evaluation.json --markdown-out reports/ai_authorship_evaluation.md

The benchmark builds balanced positive and negative handle pairs from data/handles.csv using actor_id_ground_truth only as the evaluation label. The ground-truth label is not passed to the authorship engine.

## Metrics

The benchmark reports:

- Accuracy
- Precision
- Recall
- F1
- ROC-AUC
- False positives / false negatives
- Decision-threshold summary
- Number of evaluated and skipped pairs

## Methodological boundary

The current repository does not document an independent holdout dataset for the bundled joblib artifacts. The resulting numbers are therefore a reproducible synthetic-dataset benchmark, not independent generalization performance.

For a deployment-grade validation study, evaluate the same model artifacts on an actor-disjoint dataset that was not used during model development and retain the split/provenance alongside the metrics.
