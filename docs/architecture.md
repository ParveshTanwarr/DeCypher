# System Architecture

## High-level flow

```text
Controlled / Synthetic Evidence
            |
            v
      PostgreSQL Evidence Store
            |
            v
       FastAPI Backend
        /          \
       v            v
   NLP / AI       Neo4j Graph
       \            /
        v          v
        Investigation Dashboard
             (React/Vite)
```

## Components

### Evidence and ingestion
Synthetic project datasets and authorized, controlled scanner observations provide actors, handles, wallets, posts, infrastructure indicators and observation records.

### PostgreSQL
Stores structured application and evidence records and provides deterministic persistence for the backend services.

### FastAPI backend
Provides authentication, actor/search APIs, scanner ingestion, NLP integration, correlation services and graph synchronization.

### NLP / authorship engine
The NLP service loads the project's trained authorship artifacts and compares text associated with handles. Its result is one evidence signal within the larger correlation model.

### Neo4j
Represents relationships between actors, handles, wallets, marketplaces, observations, infrastructure, PGP keys and trust/signature links as an evidence graph for investigator exploration.

PGP fingerprints from the synthetic handle dataset are normalized into PGPKey nodes and connected with (:Handle)-[:HAS_PGP_KEY]->(:PGPKey). Synthetic trust/signature evidence is represented as (:Handle)-[:TRUSTS]->(:Handle) and (:PGPKey)-[:TRUSTS]->(:Handle) relationships, with source, confidence and observation-window metadata retained in PostgreSQL and Neo4j.

### React/Vite frontend
Provides the investigation dashboard, actor investigation view, correlation results and graph exploration interface.

## Correlation model

The main evidence signals are wallet reuse, infrastructure reuse, TLS reuse, banner matching, descriptor timing and stylometric similarity. Available evidence is combined using transparent weighted scoring.

The separate operational priority model uses risk severity, correlation strength, evidence confidence, recency and evidence coverage to help investigators triage cases.

## Safety boundary

The demonstration environment uses synthetic data and controlled test infrastructure. The platform is intended for authorized investigative and defensive use and does not treat a correlation score as proof of real-world identity.


## Autonomous scanning

For authorized controlled infrastructure, the collection path now supports an asynchronous
worker architecture:

```
ScanTarget schedule
       |
       v
Celery Beat -> Redis -> Celery Worker
                         |
                         v
                  Level-2 scanner
                    /    |    \
                   v     v     v
             PostgreSQL  Neo4j  Correlation
                              |
                              v
                        Priority update
```

Autonomous scanning is disabled by default and accepts only hosts explicitly listed in
`AUTOSCAN_ALLOWED_HOSTS`. The repository default is loopback-only for the controlled SIH
demo environment.

## Temporal evidence graph

The temporal layer materializes normalized point-in-time events from timestamps already present in
the controlled evidence store. Each event records an actor, event type, entity reference, source
and timestamp in PostgreSQL as a TemporalEvent record. The same events are projected into Neo4j
as:

```
(:Actor)-[:HAS_EVENT]->(:Event)
```

This creates a queryable temporal evidence layer without inventing activity that the source data
does not contain. The actor timeline API is available at
`GET /analytics/actors/{actor_id}/timeline`.

## Structural graph anomaly analysis

The analytics service computes population-relative structural outlier signals from graph and
evidence relationships. Current features include cross-actor wallet reuse, PGP reuse, trust
degree, infrastructure reuse, marketplace switching, overlapping handle windows, and observation
source diversity. Each feature is converted to an upper-tail percentile score and combined using
transparent weights.

The result is a triage signal for investigator review. It is not a person-identity classifier,
a causal model, or proof of attribution.

Endpoints:

- `GET /analytics/actors/{actor_id}/graph-anomaly`
- `GET /analytics/graph-anomalies`
- `GET /analytics/actors/{actor_id}/timeline`

## Observability

The backend exposes Prometheus metrics at `/metrics`. The local Docker Compose environment now
includes Prometheus and Grafana provisioning for API throughput, latency, status rates and other
FastAPI instrumentation.

## Validation boundary

The repository remains a controlled demonstration system. Its datasets are synthetic or
explicitly authorized test data. Real-world attribution accuracy, live dark-web collection,
external blockchain anchoring, and production-scale streaming infrastructure are not claimed by
these components.
