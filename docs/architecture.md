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
Represents relationships between actors, handles, wallets, marketplaces, observations and infrastructure as an evidence graph for investigator exploration.

### React/Vite frontend
Provides the investigation dashboard, actor investigation view, correlation results and graph exploration interface.

## Correlation model

The main evidence signals are wallet reuse, infrastructure reuse, TLS reuse, banner matching, descriptor timing and stylometric similarity. Available evidence is combined using transparent weighted scoring.

The separate operational priority model uses risk severity, correlation strength, evidence confidence, recency and evidence coverage to help investigators triage cases.

## Safety boundary

The demonstration environment uses synthetic data and controlled test infrastructure. The platform is intended for authorized investigative and defensive use and does not treat a correlation score as proof of real-world identity.
