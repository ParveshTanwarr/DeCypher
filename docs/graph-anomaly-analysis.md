# Structural Graph Anomaly Analysis

DeCypher includes a deterministic population-relative anomaly layer to surface unusual graph
structures for investigator review.

## Features and weights

| Feature | Weight |
| --- | ---: |
| Cross-actor wallet reuse | 0.25 |
| Shared PGP reuse | 0.20 |
| Trust degree | 0.15 |
| External infrastructure reuse | 0.15 |
| Marketplace switching | 0.10 |
| Temporal handle overlap | 0.10 |
| Observation source diversity | 0.05 |

For each actor, a feature's value is ranked against the current actor population. Values above
the 80th percentile receive an upper-tail score from 0 to 100. The weighted result is bounded
to 0–100.

## API

- `GET /analytics/actors/{actor_id}/graph-anomaly`
- `GET /analytics/graph-anomalies?limit=25`

The actor endpoint returns feature values, population percentiles, tail scores, contributing
features and the methodology note.

## Interpretation

This analysis is deliberately transparent and population-relative. It is a structural triage
signal; it is not a calibrated probability, an identity determination, or a causal explanation.
A high score means the observed structure is unusual relative to this controlled population, not
that the actor has been established as a particular real-world person.

## Validation

Automated tests cover endpoint authentication, bounded scores, population output and repeated
temporal-event materialization.
