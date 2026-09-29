# DeCypher — Dark-Web Threat Actor Intelligence Platform

![SIH 2026](https://img.shields.io/badge/Smart%20India%20Hackathon-2026-orange)
![PS 26151](https://img.shields.io/badge/PS-26151-red)
![React](https://img.shields.io/badge/Frontend-React%2019-61dafb)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)

> Smart India Hackathon 2026 · Problem Statement 26151 · National Technical Research Organisation (NTRO)

DeCypher is an investigator-facing platform for collecting, storing, contextualizing and querying dark-web-style threat-actor intelligence in a controlled, ethical demonstration environment.

The platform correlates actor identities across handles, wallets, PGP fingerprints, trust relationships and infrastructure observations; exposes an evidence-oriented relationship graph; provides explainable confidence/priority scoring; and exports investigation results as CSV, JSON and PDF reports.

**Safety boundary:** the repository uses synthetic datasets and authorized local/mock infrastructure. It is intended for authorized defensive, investigative and academic use. Correlation scores are leads for investigator review, not proof of real-world identity.

---

## What DeCypher provides

### Intelligence collection and storage
- Synthetic actor, handle, wallet, marketplace, trust-link and infrastructure datasets.
- PostgreSQL as the structured evidence store.
- Authorized scanner ingestion for controlled infrastructure.
- Optional asynchronous scanning through Celery + Redis.
- Actual scan timestamps surfaced as actor last-scan dates.

### Investigation and correlation
- Search by actor ID, handle, wallet or PGP fingerprint.
- Actor profiles containing:
  - primary and associated handles
  - risk category
  - confidence score
  - operational priority score
  - first/last activity
  - last scan date
  - wallets
  - marketplaces
  - PGP fingerprints
  - trust/persona relationships
  - evidence trail and sources
- Neo4j relationship graph with a PostgreSQL fallback when Neo4j is unavailable.
- Evidence-oriented links for wallets, PGP keys, trust relationships, marketplaces, observations and infrastructure.
- Transparent correlation scoring using wallet reuse, infrastructure reuse, TLS/certificate reuse, banner matches, descriptor timing and stylometric similarity.

### AI / NLP
- Domain-aware authorship attribution using the bundled PAN20 and DeCypher model artifacts.
- Explainable stylometric signals.
- Contradiction/de-confliction checks for overlapping activity windows.
- Gemini-powered **DeCypher Copilot**, scoped to the selected actor when an actor is open.
- Copilot is instructed to use only supplied DeCypher context and distinguish evidence, inference and unknowns.
- Gemini is optional; the rest of the platform does not require it.

### Investigator UX
- Dark/light theme with persistent preference.
- Dashboard with priority queue, confidence and priority summaries.
- Investigation search with frequently searched actors.
- Interactive force-directed graph.
- Actor-specific graph snapshot embedded in PDF reports.
- Notifications and investigation Copilot.
- CSV, JSON and PDF bulk/actor exports.

---

## Architecture

```text
 Synthetic / Authorized Evidence
              |
              v
       Collection / Ingestion
              |
              v
        PostgreSQL Store
          /           \
         v             v
   NLP / Correlation   Neo4j Graph
         \             /
          \           /
           v         v
        FastAPI Backend
        JWT + RBAC + Audit
              |
              v
       React / TypeScript UI
       Dashboard / Search
       Actor / Graph / Copilot
```

### Main data flow

1. Dataset or authorized scanner produces observations.
2. PostgreSQL stores the structured actor/evidence records.
3. Correlation combines independent signals into an interpretable confidence and priority result.
4. Neo4j stores relationship-oriented graph data when available.
5. The React frontend queries actor, evidence and graph endpoints.
6. Exports materialize the current result set as CSV, JSON or PDF.
7. DeCypher Copilot receives only the selected DeCypher context plus the user's question and sends it to Gemini from the backend.

---

## Technology stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Neo4j 5
- JWT authentication + RBAC
- Celery + Redis for optional autonomous scanning
- ReportLab for PDF reports
- Prometheus instrumentation
- Pytest

### AI / NLP
- scikit-learn 1.9.x-compatible model artifacts
- SciPy
- pandas / NumPy
- joblib
- PAN20 + DeCypher authorship models
- Gemini API for the optional Copilot

### Frontend
- React 19
- TypeScript
- Vite
- react-force-graph-2d
- react-router-dom
- lucide-react

---

## Repository layout

```text
DeCypher/
├── ai/nlp/
│   ├── compare_handles.py
│   └── models/                  # trained authorship artifacts
├── backend/
│   ├── app/
│   │   ├── routers/             # auth, actors, search, AI, NLP, export, scanner...
│   │   ├── services/            # correlation, graph, ingestion, NLP
│   │   ├── models/              # SQLAlchemy + Pydantic models
│   │   ├── database/            # PostgreSQL + Neo4j clients
│   │   └── workers/             # Celery tasks
│   ├── tests/
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── .env.example
├── data/                        # synthetic demo dataset
├── docs/
│   ├── architecture.md
│   └── autonomous-scanning.md
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── api/
├── infra/                       # authorized infrastructure scanner
├── mock_service/                # controlled demo service
└── submission/                  # SIH submission artifacts
```

---

## Quick start

### Prerequisites

For the **full** stack, use:

- Python **3.11+**
- Node.js 18+
- PostgreSQL
- Docker Desktop (recommended for PostgreSQL/Neo4j/Redis)
- Git

Python 3.11+ is important for the bundled scikit-learn 1.9.x model artifacts and for the autonomous worker code.

### 1. Clone

```bash
git clone https://github.com/ParveshTanwarr/DeCypher.git
cd DeCypher
```

### 2. Start infrastructure

The easiest complete setup is:

```bash
cd backend
docker compose up -d
```

This starts:
- PostgreSQL on `5432`
- Neo4j HTTP/Bolt on `7474/7687`
- Redis on `6379`

If you already run PostgreSQL locally, you can keep using it and start only the services you need.

### 3. Configure the backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

At minimum, set a non-default `SECRET_KEY`.

For the optional Copilot:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
```

**Never commit `.env` or expose the Gemini key to the frontend.** The key belongs only on the backend.

`gemini-3.6-flash` is a stable Gemini API model. See Google's current model documentation for the supported model IDs.

### 4. Start FastAPI

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

API:
- http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

### 5. Start the frontend

In another terminal:

```bash
cd frontend
npm install
npm run build
npm run dev
```

Frontend:
- http://localhost:5173

The production build command is:

```bash
npm run build
```

---

## Demo authentication

The repository contains development/demo users used by the test suite:

| Username | Password | Intended role |
|---|---|---|
| `analyst` | `analystpassword` | investigation/read access |
| `admin` | `adminpassword` | administrative access |
| `scanner_service` | service development key | scanner/service integration |

These are **development credentials only**. Replace them and the default signing secret before any non-demo deployment.

---

## API surface

All protected endpoints require a bearer JWT. `/health` and `/auth/token` are public.

### Authentication
```text
POST /auth/token
```

### Actors and evidence
```text
GET /actors
GET /actors/{actor_id}
GET /actors/{actor_id}/evidence
GET /actors/{actor_id}/graph
```

### Search
```text
GET /search?q=<actor|handle|wallet|PGP>
```

### Correlation
```text
GET /correlation/actor/{actor_id}
GET /correlation/actors
```

Optional actor correlation parameters:

```text
handle_a=<handle>
handle_b=<handle>
```

### NLP
```text
POST /nlp/compare
```

### AI Copilot
```text
POST /ai/chat
```

Request shape:

```json
{
  "message": "Summarize this actor",
  "actor_id": "A00001",
  "history": []
}
```

The backend constructs the actor context and calls Gemini server-side. No Gemini credential is sent to the browser.

### Export

Bulk exports are available to authorized investigator/admin roles:

```text
GET /export/csv
GET /export/json
GET /export/report

GET /export/actor/{actor_id}/csv
GET /export/actor/{actor_id}/json
GET /export/actor/{actor_id}/report
POST /export/actor/{actor_id}/report
```

The actor PDF endpoint can accept an optional browser-generated graph snapshot.

### Scanner / autonomous scanning

```text
GET  /scanner/observations
POST /scanner/observations

GET  /scanner/targets
POST /scanner/targets
POST /scanner/targets/{target_id}/run

GET /scanner/jobs
GET /scanner/jobs/{job_id}
```

Autonomous scanning is disabled by default and restricted to hosts listed in `AUTOSCAN_ALLOWED_HOSTS`.

---

## Database and graph model

### PostgreSQL

The structured store contains entities including:

- Actors
- Dark-web handles
- Wallets
- Marketplaces
- PGP keys
- Trust links
- Scan targets
- Scan jobs
- Observations
- Investigator feedback
- Audit logs

### Neo4j

The evidence graph includes relationships such as:

```text
(:Actor)-[:USES_HANDLE]->(:Handle)
(:Handle)-[:USED_WALLET]->(:Wallet)
(:Handle)-[:USES_MARKETPLACE]->(:Marketplace)
(:Handle)-[:HAS_PGP_KEY]->(:PGPKey)
(:Handle)-[:TRUSTS]->(:Handle)
(:PGPKey)-[:TRUSTS]->(:Handle)
(:Actor)-[:HAS_OBSERVATION]->(:Observation)
(:Observation)-[:EVIDENCE_OF]->(:Infrastructure)
```

The graph endpoint falls back to a PostgreSQL-derived graph when Neo4j is unavailable. This keeps the investigation UI usable for local demos without requiring Neo4j.

---

## Dataset

The repository contains a fully synthetic dataset. It is designed to demonstrate correlation and attribution workflows without using real dark-web content.

| File | Approx. contents |
|---|---|
| `actors.csv` | 600 ground-truth actor profiles |
| `handles.csv` | synthetic persona/handle records |
| `wallets.csv` | synthetic wallet associations |
| `posts.csv` | 115,000 synthetic marketplace-style posts |
| `infrastructure_indicators.csv` | 250 synthetic Level-2 findings |
| `marketplaces.csv` | 20 marketplace reference records |
| `trust_links.csv` | synthetic PGP/trust relationships |

See [data/README.md](data/README.md) for the dataset contract and intended use.

---

## AI / NLP model

The authorship pipeline combines:
- PAN20-trained authorship model
- DeCypher-trained authorship model
- domain detector
- character and word TF-IDF vectorizers
- stylometric/token features
- model-specific thresholds

The bundled `.joblib` files are trusted project artifacts. Do not load untrusted joblib/pickle files.

### Important model compatibility requirement

The bundled artifacts were serialized with scikit-learn **1.9.0**. Persisted scikit-learn models are not a supported cross-version interface; use the same dependency family as the training environment or retrain/re-export the artifacts.

The repository's current `backend/requirements.txt` uses a lower bound rather than a strict pin, so reproducible deployment should pin the exact ML environment used for the artifacts.

---

## Scoring model

### Correlation confidence

Available evidence signals are combined with transparent weights:

| Signal | Weight |
|---|---:|
| Wallet reuse | 0.25 |
| Infrastructure reuse | 0.20 |
| TLS/certificate reuse | 0.15 |
| Banner match | 0.10 |
| Descriptor timing | 0.10 |
| Stylometry | 0.20 |

The system normalizes over the signals actually available for the actor. This is an interpretable evidence-fusion score, **not a calibrated probability of identity**.

### Operational priority

Priority combines:

- risk severity — 30%
- correlation — 25%
- evidence confidence — 20%
- recency — 15%
- evidence coverage — 10%

Priority is a triage score used to order investigation work. It is not an identity probability.

---

## Autonomous scanning

Autonomous scanning is deliberately opt-in.

Set:

```env
AUTOSCAN_ENABLED=true
AUTOSCAN_DEFAULT_INTERVAL_MINUTES=180
AUTOSCAN_ALLOWED_HOSTS=127.0.0.1,localhost
```

Then run:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

On Windows, the worker documentation uses the `--pool=solo` option.

Only scan infrastructure that you own or are explicitly authorized to test. Do not add third-party or public targets to the allowlist.

See [docs/autonomous-scanning.md](docs/autonomous-scanning.md).

---

## Testing

Backend tests require a disposable PostgreSQL database.

```bash
cd backend
pytest
```

Neo4j is not required for the graph unit tests; the API has a PostgreSQL fallback.

Frontend:

```bash
cd frontend
npm run build
npm run lint
```

---

## Repository audit — 29 September 2026

A repository-wide static review was performed against the tracked source tree, configuration, dependency manifests, tests and documentation. The following are the known issues that matter for a local/demo deployment.

### 1. Correlation / stylometry currently has a dependency-version mismatch

The bundled ML artifacts were serialized with scikit-learn 1.9.0. Running them under scikit-learn 1.6.1 produces an `InconsistentVersionWarning` and the current domain detector can fail with:

```text
AttributeError: 'LogisticRegression' object has no attribute 'multi_class'
```

**Impact:** `GET /correlation/actor/{actor_id}` can fail when it invokes the trained NLP engine.

**Correct resolution:** run the model under the matching 1.9.x environment or retrain/re-export the artifacts under the target environment. Do not rely on the lower-bound `scikit-learn>=1.4.0` constraint for reproducibility.

### 2. Python 3.9 is not a full-stack supported environment

Some worker code uses Python 3.10+ type syntax such as `str | None` and `list[dict[...]]`. The bundled scikit-learn 1.9 artifacts additionally require a Python 3.11+ environment for a supported installation.

**Recommendation:** use Python 3.11+ for the complete application.

### 3. Neo4j is optional at runtime, but must be running for the native graph path

If Neo4j is unavailable, the actor graph endpoint falls back to PostgreSQL-derived relationships.

**Impact:** the graph UI still works, but Neo4j-specific persistence/synchronization and some richer graph behavior are unavailable.

Start it with:

```bash
cd backend
docker compose up -d neo4j
```

### 4. Redis/Celery are required only for autonomous scanning

The normal FastAPI + PostgreSQL + frontend workflow does not require a Celery worker. Autonomous scanning does.

If Redis/Celery are not running, the core dashboard remains usable, but queued autonomous scan jobs cannot execute.

### 5. Production CORS configuration should be tightened

The current development API allows all origins and credentials. This is convenient for local development but should be replaced with an explicit frontend origin list before production deployment.

### 6. Development secrets are intentionally present as defaults

The configuration contains development defaults for database credentials, Neo4j credentials and JWT signing. The application warns when the default JWT secret is still active.

These values are acceptable for the controlled demo setup only. They must be replaced for deployment outside the local/demo environment.

### 7. Gemini Copilot depends on external API availability

The Copilot is server-side and optional. A missing/invalid key, unavailable Gemini endpoint, quota/rate limit or network timeout can make `/ai/chat` fail while the rest of DeCypher continues to operate.

The API key should remain in `backend/.env` and must never be committed to Git or exposed in frontend code.

---

## Security and ethical boundary

DeCypher is designed around an evidence-first workflow:

- Synthetic demo data is used for the bundled dataset.
- Scanner targets are allowlisted.
- Autonomous scanning is disabled by default.
- API access is authenticated with JWTs.
- Investigator/admin permissions are applied to protected operations.
- Requests are audit logged.
- Correlation scores are presented as investigative evidence signals, not proof of identity.
- Infrastructure attribution is demonstrated only against controlled/authorized targets.

Never use the scanner against infrastructure without authorization.

---

## Documentation

- [Architecture](docs/architecture.md)
- [Autonomous scanning](docs/autonomous-scanning.md)
- [Synthetic dataset](data/README.md)
- [Backend tests](backend/tests/README.md)

---

## Status

DeCypher is a Smart India Hackathon prototype. The local demo path is:

```text
Login
  ↓
Dashboard
  ↓
Investigation Search
  ↓
Actor Profile
  ├── Evidence Trail
  ├── Correlation / Priority
  ├── Relationship Graph
  ├── CSV / JSON / PDF export
  └── Gemini-powered Copilot
```

The platform is intended to demonstrate an end-to-end intelligence workflow rather than claim autonomous real-world attribution.
