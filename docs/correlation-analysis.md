# Counterfactual Correlation and Source Reliability

DeCypher exposes two evidence-analysis layers on top of its transparent weighted correlation score.

## Counterfactual sensitivity

The correlation engine performs leave-one-signal-out analysis for every signal that is currently available.

For each signal, it reports:

- baseline evidence score
- score after removing that signal
- score delta
- absolute sensitivity
- remaining signal count and weight

A positive delta means the removed signal was supporting the baseline score. A negative delta means the removed signal was below the current weighted average, so removing it raises the score.

This is a **sensitivity analysis of the scoring rule**. It is not a causal analysis, and it does not establish that a signal caused an actor association.

API:

`GET /correlation/actor/{actor_id}/counterfactual`

The normal actor correlation response also includes the same counterfactual block.

## Review-conditioned source reliability

Observation-based signals now use a source-reliability multiplier derived from investigator feedback on **other actors**.

The estimator is intentionally conservative:

- prior reliability = 0.50
- prior strength = 4 reviewed cases
- confirmed verdicts increase the posterior
- false-positive/reject/dismiss verdicts decrease the posterior
- current actor feedback is excluded from the estimate
- reliability is bounded to [0.25, 0.90]
- the resulting confidence multiplier is bounded to [0.75, 1.20]

Only actors that have observable evidence from a source contribute to that source's review pool.

The reliability value is a **review-conditioned operational estimate**, not an independently validated measure of source truthfulness. It should not be described as ground truth or as a causal source-quality measurement.

Source metadata is returned in:

`GET /correlation/actor/{actor_id}`

and

`GET /correlation/actor/{actor_id}/counterfactual`

The frontend shows both the posterior estimate and the multiplier used by the observation-based signal calculation.

## Data safeguards

Synthetic startup evidence is excluded from correlation when the repository's configured demo-evidence exclusion is enabled. This exclusion is also respected by source-reliability estimation.

Leave-one-actor-out estimation reduces direct feedback leakage: an actor's own investigator verdict does not update the source reliability used for that same actor.
