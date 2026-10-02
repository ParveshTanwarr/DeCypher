# Temporal Evidence Analytics

DeCypher's temporal layer is an evidence-normalization mechanism rather than a temporal inference
engine.

## Event sources

Events are materialized from timestamps already stored in the controlled dataset:

- handle registration / first-seen / last-seen
- PGP first-seen / last-seen
- wallet first-seen
- trust-link first-seen / last-seen
- observation timestamps
- completed authorized scan timestamps

Each materialized event has a deterministic `event_key`, so startup backfills are idempotent.

## Storage and graph projection

PostgreSQL is the source of truth in the `temporal_events` table. The same events are projected
into Neo4j as `Event` nodes connected to their owning actor with `HAS_EVENT`.

When Neo4j is unavailable, timeline APIs continue to work from PostgreSQL. The event projection is
best-effort and logged as deferred rather than making the evidence store unavailable.

## API

`GET /analytics/actors/{actor_id}/timeline`

Query parameters:

- `start`: optional ISO-8601 lower bound
- `end`: optional ISO-8601 upper bound
- `limit`: 1–1000, default 250

The response includes event counts by type, ordered events, sources and a methodology note.

## Evidence boundary

Only observed timestamps are materialized. The service does not create synthetic “activity”
between observations and does not fill unknown periods.
