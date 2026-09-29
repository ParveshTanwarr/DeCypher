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

A repository-wide static review of the tracked source tree identified the following repository-level issues. Local-machine setup problems are intentionally excluded.

### Fixed in the current remediation pass

- Scanner evidence is now resolved consistently from actor ID, primary/associated handles, and linked scan-target URL/name across actor detail, evidence, graph, correlation and bulk export paths.
- Correlation observation queries are scoped to actor evidence instead of repeatedly scanning the entire observation table; wallet-reuse lookups are batched; `correlate_all()` commits once after processing.
- Bulk export now fetches only detected observations matching the actors and their known evidence targets.
- Native Neo4j graph query map literals no longer contain duplicate keys.
- Neo4j actor-graph synchronization now supplies stable `handle_id` values, so live graph sync can populate handle and wallet relationships correctly.
- The PostgreSQL graph fallback batches wallet-reuse lookup instead of querying once per wallet.
- Backend and frontend graph contracts now share explicit node `type` and relationship `relation` fields.
- Credentialed CORS is now restricted to an explicit environment-configured frontend-origin allowlist.
- The duplicate `backend/app/routers/.env.example` template has been removed; `backend/.env.example` is the canonical configuration template.

### Intentionally deferred for the AI/NLP pass

- Actor-scoped Gemini context still contains the known `ScanTarget.url` vs `ScanTarget.target_url` mismatch.
- The NLP service's fallback heuristic and persisted scikit-learn artifact/runtime compatibility remain unchanged.
- AI/NLP-specific evidence-scope unification is not part of this remediation pass.

### Deployment-only concerns retained

- Demo bcrypt credentials and development database/Neo4j defaults remain intentionally present for the hackathon/demo environment. They must not be reused as production secrets; the application already warns when the checked-in JWT secret is still active.
- The synthetic dataset, controlled scanner, optional Neo4j fallback and optional Redis/Celery autoscan infrastructure remain deliberate prototype choices rather than correctness failures.

## Functional issues

#### 1. Actor-scoped Gemini context references a non-existent field
'backend/app/routers/ai.py' builds scan-target context with 't.url', but the SQLAlchemy model defines the field as 'ScanTarget.target_url'.

**Impact:** an actor-scoped 'POST /ai/chat' request can raise an 'AttributeError' when the actor has scan targets.

**Fix:** replace both 't.url' references with 't.target_url'.

#### 2. Correlation ignores URL/name-based scanner observations
The actor evidence endpoint correctly expands its observation lookup to include each actor's scan-target URL and name. The correlation service does not: its observation scoring, evidence-confidence and recency paths only match the actor ID/primary/associated handles.

**Impact:** legitimate scanner evidence can appear in the Actor Evidence view but fail to contribute to correlation/priority scoring.

**Fix:** centralize actor observation-target resolution and use it consistently across evidence, correlation, priority and Copilot context.

#### 3. Neo4j graph query contains duplicate map keys
The native Neo4j query in 'backend/app/services/graph_service.py' contains repeated 'handle_id' keys in returned map literals.

**Impact:** this is invalid/redundant Cypher map construction and can break the native Neo4j graph path. The API may then silently fall back to the PostgreSQL graph.

**Fix:** remove the duplicate keys from 'handle_pgp_keys' and 'handle_marketplaces'.

#### 4. Wallet graph filtering contains a duplicated condition
'sync_actor_batch()' checks 'w.get("handle_id")' twice when constructing wallet rows.

**Impact:** no current functional change, but it is redundant logic and a maintenance smell.

**Fix:** keep a single 'handle_id' check.

### Performance / scalability issues

#### 5. Correlation performs repeated full-table scans
'CorrelationService' repeatedly loads large sets of observations and then filters them in Python. Wallet reuse also performs a query for every wallet. 'correlate_all()' then runs the complete correlation flow actor-by-actor and commits each result.

**Impact:** acceptable for the synthetic demo dataset, but it will scale poorly as observation, wallet and actor counts grow.

**Fix:** push filtering/grouping into SQL, batch related records, cache actor evidence targets, and commit priority updates in batches.

#### 6. Bulk export loads all detected observations
The export service preloads every detected observation before assigning records to actors.

**Impact:** memory and query cost grow with the global observation table even when exporting a subset.

**Fix:** fetch observations scoped to the actor IDs/targets being exported, preferably with a single indexed query.

#### 7. Correlation can fall back to an unvalidated heuristic
The NLP service intentionally fails soft when the trained model artifacts cannot be loaded and uses a basic word-overlap heuristic.

**Impact:** the API can remain available while producing a score that is materially different from the validated authorship model.

**Fix:** expose the engine mode in the response and clearly distinguish 'trained_model' from 'fallback_heuristic', or fail the stylometry signal explicitly instead of silently substituting it.

### Security / deployment issues

#### 8. CORS is unrestricted
'backend/app/main.py' currently uses 'allow_origins=["*"]' together with credentials.

**Impact:** appropriate for a local prototype, not an appropriate production policy.

**Fix:** configure an explicit frontend-origin allowlist through environment settings.

#### 9. Development credentials and secrets are embedded in application defaults
Demo bcrypt credentials are intentionally present in 'auth.py', while database/Neo4j/JWT development defaults exist in configuration/example files.

**Impact:** these values must never be treated as production credentials.

**Fix:** move real credentials to environment/secret management and keep demo credentials clearly isolated from production deployment.

#### 10. A second '.env.example' exists inside 'backend/app/routers/'
'backend/app/routers/.env.example' duplicates configuration and contains a development JWT secret.

**Impact:** configuration is duplicated and the secret-like material is located inside the application package where it does not belong.

**Fix:** remove the nested file and keep the canonical template at 'backend/.env.example'.

### Maintainability / correctness issues

#### 11. Scan-target lookup logic is duplicated across services
Actors, exports, AI context, correlation and scanner code each implement slightly different notions of what observations belong to an actor.

**Impact:** different screens can disagree about the evidence attached to the same actor.

**Fix:** create one reusable service/helper that resolves actor ID, primary handle, associated handles, scan-target URLs and scan-target names.

#### 12. Graph response contracts are looser on the frontend than on the backend
The backend 'GraphNode' schema requires 'id', 'label', 'name' and 'category', while the frontend client treats 'name', 'category' and 'type' as optional and performs runtime normalization.

**Impact:** the UI is compensating for an inconsistent API contract.

**Fix:** define one canonical graph-node contract and use it consistently across backend schema, fallback graph, Neo4j graph mapping and TypeScript types.

### Compatibility / reproducibility issue

#### 13. Persisted ML artifacts need a pinned training/runtime environment
The authorship '.joblib' artifacts are serialized scikit-learn models. The repository's lower-bound dependency specification is not enough to guarantee that persisted models can be loaded with every allowed scikit-learn release.

**Impact:** fresh installations can load the API successfully while the stylometry/correlation engine fails or emits compatibility warnings.

**Fix:** pin the exact model-training dependency set, or publish a reproducible model-training/export environment alongside the artifacts.

### What is *not* considered an error

- Neo4j being unavailable is **not** a correctness failure because a PostgreSQL graph fallback is intentionally implemented.
- Redis/Celery being absent is **not** a core-platform failure because autonomous scanning is optional and disabled by default.
- The synthetic dataset and controlled scanner are deliberate design choices for the prototype.
- Development credentials in the test suite are expected; they are only a deployment concern if reused outside the demo environment.

### Priority for remediation

1. **Functional:** AI scan-target field, scanner evidence participation in correlation, Neo4j duplicate map keys.
2. **Correctness/consistency:** centralized actor-evidence target resolution and explicit NLP fallback state.
3. **Scalability:** correlation queries and export observation loading.
4. **Security/deployment:** CORS and secret/configuration cleanup.
5. **Maintainability:** canonical graph contract and removal of duplicated configuration.

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
