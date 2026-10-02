# Behavioural Profiling

DeCypher's behavioural profile is a descriptive, evidence-backed view of an actor's recorded activity. It reuses the existing NLP feature implementation and PostgreSQL actor, handle, wallet, PGP, trust-link, and observation records.

## Dimensions

- **Linguistic:** per-post style features from the same `style_features` implementation used by the trained authorship engine, aggregated by handle and across handles. Raw post text is not included in the API response or profile snapshots.
- **Temporal lifecycle:** handle registration/first-seen and last-seen windows, account status distribution, overlapping handle windows, and inter-handle gaps.
- **Operational:** marketplace footprint, wallet reuse within an actor, wallet addresses shared with other actor records, and PGP-key associations beyond the actor's handles.
- **Interaction:** incoming/outgoing recorded trust-link edges, relationship types, counterparties, and recorded edge confidence.
- **Infrastructure:** counts and types of detected, provenance-tagged infrastructure observations. Synthetic UI filler observations are excluded.

## API

All routes require an authenticated user.

- `POST /actors/{actor_id}/behavioral-profile/refresh` — build the current profile and store a snapshot when its source fingerprint changes.
- `GET /actors/{actor_id}/behavioral-profile` — retrieve the latest stored profile and up to ten snapshot history entries.

The snapshot stores a profile version, source fingerprint, coverage score, generated timestamp, and structured profile data. Repeating a refresh against unchanged source data is idempotent.

## Behavioural drift

When a new source fingerprint is stored, the service compares it with the previous snapshot. It reports descriptive numeric linguistic feature deltas and changes to selected operational counts. It does not classify a change as malicious, anomalous, or proof of account takeover.

## Interpretation and limitations

- The bundled dataset is synthetic and is for controlled prototype demonstrations.
- The current `posts.csv` profiling path has no usable per-post event timestamp. Posting hours, weekday routines, and posting cadence are therefore unavailable.
- Handle registration and last-active values describe lifecycle windows, not continuous activity.
- Similarity, shared wallets, PGP associations, and trust links are investigative leads. They do not prove that records represent the same person.
- The service reports whether the trained authorship model or fallback heuristic was used. Fallback output must not be represented as validated-model output.
- Coverage is a measure of available data dimensions, not a confidence score or identity probability.
