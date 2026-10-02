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
- Tamper-evident SHA-256 evidence ledger with append-only chain verification.
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

### Evidence integrity
- SHA-256 hash-chained observation ledger stored in PostgreSQL.
- PostgreSQL advisory locking for serialized ledger appends.
- Full-chain verification endpoint and actor-facing integrity status.
- Optional external blockchain anchoring is not configured in the bundled prototype.

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
6. Observations are written to PostgreSQL and the tamper-evident evidence ledger in the same transaction.
7. Exports materialize the current result set as CSV, JSON or PDF.
8. DeCypher Copilot receives only the selected DeCypher context plus the user's question and sends it to Gemini from the backend.

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
│   ├── autonomous-scanning.md
│   ├── behavioral-profiling.md
│   └── evidence-integrity.md
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
- Node.js 20.19+ or 22.12+
- PostgreSQL
- Docker Desktop (recommended for PostgreSQL/Neo4j/Redis)
- Git

Python 3.11+ is important for the bundled scikit-learn 1.9.x model artifacts and for the autonomous worker code.

### 1. Clone

```bash
git clone https://github.com/ParveshTanwarr/DeCypher.git
cd DeCypher
```

### 2. Configure the backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set a unique `SECRET_KEY` before starting the API. The Dockerized Celery worker/beat services also read this `.env`. The example disables autonomous scanning by default and excludes startup-only synthetic filler evidence from correlation by default.

For the optional Copilot:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
```

**Never commit `.env` or expose the Gemini key to the frontend.** The key belongs only on the backend.

### 3. Start infrastructure

The complete demo stack is:

```bash
cd backend
docker compose up -d
```

This starts:
- PostgreSQL on `5432`
- Neo4j HTTP/Bolt on `7474/7687`
- Redis on `6379`
- Celery worker and Celery Beat for autonomous scanning

If you already run PostgreSQL locally, you can keep using it and start only the services you need.

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

### Windows PowerShell note

The commands above use POSIX-style virtual-environment activation. On Windows PowerShell, use:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks the activation script, you can either activate the environment from a Command Prompt with `\.venv\Scripts\activate.bat` or run the Python commands through `\.venv\Scripts\python.exe` directly.

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
GET /integrity/status
GET /integrity/verify
GET /integrity/ledger
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

The repository pins `scikit-learn==1.9.0` to match the bundled model artifacts. Keep that version aligned with the training environment when loading the persisted models.

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

## Repository audit — 30 September 2026

A repository-wide review was completed for the submission build. The core non-AI/NLP issues identified in the previous audit have been remediated.

### Resolved in the submission build

- Scanner evidence resolution is shared across actor detail, evidence, graph, correlation and export paths.
- Correlation observation queries are scoped to actor evidence; wallet reuse lookups are batched; full correlation commits once after processing.
- Bulk exports fetch only observations relevant to the exported actors.
- Native Neo4j graph map construction was cleaned up and graph synchronization uses stable handle IDs.
- PostgreSQL graph fallback remains available when Neo4j is unavailable.
- Backend/frontend graph contracts now use explicit node `type` and edge `relation` fields.
- Credentialed CORS is restricted to the configured frontend-origin allowlist and exposes `Content-Disposition` for browser downloads.
- Duplicate configuration templates were removed; `backend/.env.example` is canonical.
- Frontend export controls now use non-submit buttons, prevent duplicate export actions, close cleanly on outside click/Escape, and keep browser object URLs alive through the download hand-off.
- Dashboard priority queue now renders all indexed actors in priority order inside an isolated scroll region; the surrounding dashboard remains fixed.
- Dashboard notifications now surface the synchronized actor feed, priority updates and the top-ranked actors as active unread items.
- On backend startup, every actor is guaranteed a four-signal synthetic investigation evidence trail for the controlled demo; existing evidence is preserved and missing signals are added idempotently. These filler observations are excluded from correlation by default so they cannot silently inflate attribution scores.

### AI/NLP boundary for the submission build

The stylometry/NLP implementation has not been modified. The bundled authorship artifacts, fallback heuristic, feature extraction and model/runtime compatibility behavior remain unchanged.

The Gemini Copilot received only a targeted context fix: actor scan-target context now uses the actual `ScanTarget.target_url` field, actor observations are resolved through the same evidence-target helper as the rest of the backend, and request failures are surfaced as a clean API error instead of an unhandled exception.

### Deployment-only notes

- Development credentials and local database/Neo4j defaults remain intentionally available for the hackathon/demo environment. They must not be reused for production deployment.
- The synthetic dataset, controlled scanner, Neo4j fallback and optional Redis/Celery autoscan path are deliberate prototype/demo choices rather than core correctness failures.
- Exact dependency pinning for persisted ML artifacts remains a reproducibility concern for a future deployment-focused pass.

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
- [Behavioural profiling](docs/behavioral-profiling.md)
- [Evidence integrity](docs/evidence-integrity.md)
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


## Behavioural profiling

The authenticated actor workspace includes an evidence-backed behavioural profile covering linguistic style, account lifecycle, operational footprint, recorded trust relationships, and infrastructure observations. Profiles are versioned and fingerprinted in PostgreSQL; changed source data creates a new snapshot and a descriptive comparison against the previous profile.

See [docs/behavioral-profiling.md](docs/behavioral-profiling.md) for endpoints, feature definitions, and interpretation limits. The bundled dataset is synthetic, and post-level activity cadence is not inferred because the current post records do not provide usable event timestamps.
