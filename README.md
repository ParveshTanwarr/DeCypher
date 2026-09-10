# 🕸️ DeCypher — Dark Web Threat Actor De-Anonymization Platform

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Smart India Hackathon](https://img.shields.io/badge/SIH-2026-orange.svg)
![Problem Statement](https://img.shields.io/badge/PS-26151-red.svg)
![Theme](https://img.shields.io/badge/theme-Blockchain%20%26%20Cybersecurity-6a1b9a.svg)

> **Smart India Hackathon 2026** — Problem Statement #26151
> Dark Web Threat Actor De-Anonymization
> National Technical Research Organisation (NTRO)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Solution Architecture](#-solution-architecture)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Quick Start](#-quick-start)
- [System Architecture](#-system-architecture)
- [Database Schema](#-database-schema)
- [API Documentation](#-api-documentation)
- [AI / NLP — Authorship Attribution Engine](#-ai--nlp--authorship-attribution-engine)
- [Level 2 — Infrastructure Attribution](#-level-2--infrastructure-attribution)
- [Dataset](#-dataset)
- [Project Structure](#-project-structure)
- [Ethics & Legal Safeguards](#-ethics--legal-safeguards)
- [Roadmap](#-roadmap)
- [Team](#-team)

---

## 🎯 Overview

**DeCypher** is an autonomous intelligence platform that helps investigators attribute dark
web threat actors — people behind drug/arms sales, stolen-data markets, hacking services,
money laundering, and terror financing — to persistent identities and, where evidence
allows, real-world infrastructure.

### The Challenge

Threat actors on the dark web hide behind Tor hidden services, deliberately fragmenting
their identity across multiple marketplace handles and abandoning accounts the moment one
gets flagged. Investigators today correlate this manually — cross-referencing handles,
wallets, and writing style by hand — which doesn't scale and produces leads with no
structured evidence trail behind them.

### Our Solution

DeCypher continuously collects dark web footprints, correlates them into a relationship
graph, uses AI to catch actors rebranding under new handles, and — where infrastructure
leaks allow — links a known actor to real-world hosting infrastructure. Every attribution
ships with an explainable, signal-by-signal confidence score, not a black-box number.

- ✅ Links fragmented personas (handles, PGP keys, wallets) into one actor profile
- ✅ Detects rebranded/migrated accounts via stylometric AI, validated on an academic
  benchmark (92.57% accuracy)
- ✅ Surfaces infrastructure leaks (SSL cert reuse, exposed status pages, banners) pointing
  toward real-world hosting
- ✅ Every match ships with an Evidence Trail, a Priority Score, and a contradiction check
- ✅ Full investigator dashboard with graph visualization, search, and CSV/JSON export

---

## 🎓 Problem Statement

**Problem Statement ID:** 26151
**Title:** Dark Web Threat Actor De-Anonymization
**Theme:** Blockchain & Cybersecurity
**Category:** Software
**Organization:** National Technical Research Organisation (NTRO)

### Background

The dark web has become a preferred operating space for threat actors, mainly because Tor
hidden services let them hide their identity — making attribution the central challenge for
any investigation into drug/arms sales, stolen-data and hacking services, money laundering,
and terror financing conducted there.

### Required Capabilities (as specified by NTRO)

1. **Infrastructure misconfiguration detection** — exposed status pages, reused SSL
   certificates, default service banners, descriptor inconsistencies — matched against
   clearnet infrastructure to point toward likely origin servers
2. **Cross-marketplace relationship mapping** — handles, PGP keys, wallets, and trust links
   correlated into a single relationship graph
3. **AI-based persona attribution** — stylometric and behavioral analysis linking
   rebranded/migrated personas back to known actors
4. **Analytical front end** — timeline-based querying across actor profiles, identifiers,
   infrastructure indicators, persona linkages, attribution confidence, category, last scan
   date, and source, with CSV/JSON/report export

---

## 🏗️ Solution Architecture

```
                 ┌──────────────────────────┐
                 │      DATA SOURCES        │
                 │ Marketplaces & forums     │
                 │ (authorized/ethical)      │
                 │ CT logs / infra data      │
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │    COLLECTION LAYER      │
                 │ Post/identifier ingestion │
                 └────────────┬─────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌──────────────────────┐              ┌──────────────────────┐
│   AI ATTRIBUTION      │              │ INFRASTRUCTURE        │
│   (Level 1)           │              │ ATTRIBUTION (Level 2) │
│                        │              │                        │
│ Stylometric similarity │              │ Certificate matching   │
│ Domain-aware routing   │              │ Status-page detection  │
│ (PAN20 + DeCypher)     │              │ Banner fingerprinting  │
└──────────┬─────────────┘              │ Descriptor timing      │
           │                            └──────────┬─────────────┘
           └───────────────┬────────────────────────┘
                            ▼
                 ┌──────────────────────────┐
                 │   ATTRIBUTION ENGINE     │
                 │ Confidence scoring        │
                 │ Priority Score            │
                 │ Contradiction detection   │
                 └────────────┬─────────────┘
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
┌────────────────────────┐        ┌────────────────────────┐
│        NEO4J            │        │      POSTGRESQL         │
│ Actor↔Handle↔Wallet      │        │ Actors, handles, wallets│
│ relationship graph       │        │ Observations, feedback  │
└────────────┬─────────────┘        │ Audit log                │
             └────────────┬──────────┴────────────┬─────────────┘
                           ▼
                 ┌──────────────────────────┐
                 │   FASTAPI BACKEND API    │
                 │ JWT auth · RBAC · audit   │
                 │ Prometheus metrics        │
                 └────────────┬─────────────┘
                              ▼
                 ┌──────────────────────────┐
                 │   REACT INVESTIGATOR      │
                 │        DASHBOARD          │
                 │ Force-directed graph      │
                 │ Actor search & detail     │
                 │ CSV / JSON export         │
                 └──────────────────────────┘
```

### Request Flow

1. **Infra scanner / ingestion** → observations posted to `POST /scanner/observations`
2. **Correlation** → shared wallets/PGP/handles linked into the Neo4j actor graph
3. **AI attribution** → `POST /nlp/compare` scores whether two handles share an author
4. **Attribution Engine** → confidence + priority scoring, contradiction checks
5. **Investigator dashboard** → queries `/actors`, `/actors/{id}/graph`,
   `/actors/{id}/evidence`, renders the force-directed graph, exports results

---

## ✨ Key Features

### 🤖 AI-Powered Persona Attribution (Level 1)

- Domain-aware routing between two trained classifiers — one validated on the academic
  **PAN20 Authorship Verification benchmark**, one trained on DeCypher's own dataset — blended
  per-prediction by a domain detector
- **92.57% accuracy, 97.57% ROC-AUC** on the locked PAN20 test set
- **95.6% accuracy, 99.3% ROC-AUC** on actor-disjoint DeCypher evaluation (no actor seen in
  both train and test)
- Leakage-audited: a strict, vocabulary-overlap-controlled re-check still holds at 94.7%
- Every prediction returns an **Evidence Trail** — which specific signals (sentence length,
  punctuation style, function-word usage, typo rate, vocabulary richness) contributed, not
  just a bare score

### 🛰️ Infrastructure Attribution (Level 2)

- Detects Tor hidden-service misconfigurations: default service banners, exposed status
  pages, reused SSL certificates, and descriptor timing anomalies
- Matches findings against known clearnet infrastructure to generate real-world attribution
  leads
- Runs only against **authorized, self-hosted mock services** — never live marketplaces —
  tagged `source: authorized-test-service` throughout

### 🕸️ Cross-Platform Actor Correlation

- Neo4j relationship graph linking handles, wallets, and PGP keys across marketplaces
- Surfaces linked personas even when they present as unrelated accounts on the surface

### 🎯 Explainable & Prioritized Intelligence

- **Priority Score** — confidence × risk category, so investigators act on the most
  dangerous, best-evidenced actors first
- **Contradiction detection** — flags evidence that weakens a proposed match (e.g.
  conflicting activity windows) instead of only accumulating supporting evidence
- **Investigator feedback loop** — confirm/reject verdicts stored per actor, informing
  future scoring

### 🔐 Security & Governance by Design

- JWT authentication with role-based access control (bulk export restricted to `admin`)
- Every API call logged via `AuditLogMiddleware` (`username`, `method`, `endpoint`, params,
  timestamp)
- Prometheus metrics exposed via `prometheus-fastapi-instrumentator`
- No live scraping of illegal marketplaces — built and demoed entirely on ethical
  academic/synthetic datasets

---

## 🛠️ Technology Stack

### Backend

```
Python 3.x
FastAPI              — REST API framework
SQLAlchemy           — PostgreSQL ORM
neo4j (driver)       — graph database client
python-jose + bcrypt — JWT auth
prometheus-fastapi-instrumentator — metrics
pytest               — test suite
```

### AI / NLP

```
scikit-learn / scipy — classifiers, TF-IDF vectorization
pandas / numpy        — feature engineering
joblib                — model persistence
```

### Frontend

```
React 19 + TypeScript
Vite                  — build tooling
react-force-graph-2d  — interactive actor relationship graph
react-router-dom       — routing
lucide-react           — icons
```

### Databases

```
PostgreSQL 15  — actor profiles, handles, wallets, observations, audit log
Neo4j 5 (Community + GDS/APOC plugins) — correlation graph
```

### Infrastructure Attribution

```
Python + requests — banner / status-page / certificate scanning
Self-hosted mock hidden service — safe, controlled demo target
```

---

## 🚀 Quick Start

### Prerequisites

```bash
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
```

### 1. Start the databases

```bash
cd backend
docker-compose up -d      # starts Postgres (5432) + Neo4j (7474/7687)
```

### 2. Start the backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env      # fill in SECRET_KEY, DB credentials
uvicorn app.main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`, backend on `http://localhost:8000`.

### 4. Verify

```bash
curl http://localhost:8000/health
# {"status": "healthy", "service": "Threat Intel API"}
```

---

## 🏛️ System Architecture

### Backend (`backend/app/`)

```
routers/
├── auth.py       — login, JWT issuance, role-based dependency
├── actors.py      — actor list/detail/evidence/graph endpoints
├── search.py      — cross-entity search
├── feedback.py     — investigator confirm/reject verdicts
├── export.py       — CSV / JSON bulk export (admin-only)
├── scanner.py       — Level 2 observation ingestion
└── nlp.py           — Level 1 authorship comparison

services/
├── graph_service.py — Neo4j query layer
├── ingestion.py       — data loading pipeline
└── nlp_service.py      — wraps the trained attribution model

middleware/
└── audit_log.py — logs every request (who, what, when)

models/
├── sql_models.py — SQLAlchemy schema (see below)
└── schemas.py      — Pydantic request/response contracts
```

### AI / NLP (`ai/nlp/`)

```
compare_handles.py — DeCypherAuthorshipEngine: loads all trained
                      artifacts, exposes compare_handles() and
                      check_contradiction()
models/
├── pan20_expert_model.joblib        — PAN20-trained classifier
├── decypher_expert_model.joblib      — DeCypher-trained classifier
├── domain_detector_model.joblib       — routes between the two above
├── pan20_character_vectorizer.joblib
├── pan20_word_vectorizer.joblib
├── domain_vectorizer.joblib
└── model_thresholds.npz
```

### Infrastructure Attribution (`infra/`)

```
detectors/
├── banner.py             — default service banner fingerprinting
├── certificate.py         — SSL certificate fingerprint matching
├── status_page.py          — exposed status/admin page detection
└── descriptor_timing.py     — Tor descriptor timing anomalies

scanner.py            — orchestrates all detectors against a target
observation_mapper.py — maps raw findings to backend schema
backend_client.py      — posts observations to /scanner/observations
evidence.py             — local evidence persistence
```

### Frontend (`frontend/src/`)

```
pages/
├── LoginPage.tsx
├── SearchPage.tsx
├── GraphPage.tsx  — force-directed actor relationship graph
└── ActorPage.tsx   — actor detail + evidence trail

api/client.ts — typed, JWT-authenticated API client
```

---

## 🗄️ Database Schema

### PostgreSQL (structured records)

```sql
actors               -- actor_id, primary_handle, risk_category,
                      -- confidence_score, priority_score
darkweb_handles       -- handle, platform, status, first/last_seen,
                      -- stylometry_vector_hash, FK → actors
wallets               -- address, currency, associated_handle, FK → actors
marketplaces          -- name, onion_url, status
observations          -- Level 2 findings: indicator_type, target,
                      -- source, confidence, detected, timestamp
investigator_feedback -- verdict, notes, investigator_id, FK → actors
audit_logs            -- username, method, endpoint, query_params, timestamp
```

### Neo4j (relationship graph)

```
(:Actor)-[:USES_HANDLE]->(:Handle)
(:Actor)-[:SHARES_WALLET]->(:Wallet)
(:Wallet)-[:ALSO_USED_BY]->(:Handle)   -- surfaces cross-actor wallet reuse
```

---

## 🔌 API Documentation

All endpoints except `/health` and `/auth/login` require a bearer JWT.

```http
POST /auth/login                    → issue JWT

GET  /actors?category=&min_confidence=&limit=&offset=
                                     → paginated, filterable actor list
GET  /actors/{actor_id}              → full actor profile
GET  /actors/{actor_id}/evidence      → evidence signal list
GET  /actors/{actor_id}/graph          → Neo4j-backed relationship subgraph
                                        (falls back to Postgres join if
                                        Neo4j hasn't been synced)

GET  /search?q=                        → cross-entity search

POST /feedback                         → investigator confirm/reject verdict

GET  /export/json                       → bulk actor export (admin)
GET  /export/csv                         → bulk actor export (admin)

GET  /scanner/observations               → list Level 2 findings
POST /scanner/observations                → ingest new findings (deduplicated,
                                            atomic upsert)

POST /nlp/compare                          → Level 1 authorship comparison
                                            {handle_a, handle_b} →
                                            {similarity_score, is_same_author,
                                             confidence, shared_linguistic_markers}

GET  /health                                → liveness check
GET  /metrics                                → Prometheus metrics
```

---

## 🧠 AI / NLP — Authorship Attribution Engine

DeCypher's Level 1 attribution uses a **domain-aware routing pipeline**: two independently
trained classifiers — one on the published PAN20 Authorship Verification benchmark, one on
DeCypher's own synthetic marketplace-style dataset — blended per-prediction by a domain
detector that judges how "PAN-style" vs "DeCypher-style" the input text looks.

| Evaluation | Result | What it proves |
|---|---|---|
| PAN20 held-out test set (locked, never tuned against) | **92.57% accuracy, 97.57% ROC-AUC** | Validated against an independent academic benchmark |
| DeCypher dataset, actor-disjoint split | **95.6% accuracy, 99.3% ROC-AUC** | Generalizes to unseen actors, not memorized ones |
| DeCypher dataset, strict leakage-controlled audit | **94.7% accuracy** | Holds up after removing trivially-overlapping pairs |

**Known limitation, tested and documented rather than hidden:** a PAN20-trained model does
not automatically transfer to a completely different, unseen writing-style dataset without
recalibration — a documented phenomenon in authorship-verification research called domain
shift. This is precisely why the architecture includes autonomous rescanning and an
investigator feedback loop, rather than relying on one static, frozen model.

Every comparison returns a full **Evidence Trail**:

```json
{
  "same_author_probability": 99.95,
  "is_likely_match": true,
  "domain_routing": {"decypher_weight": 0.985, "pan_weight": 0.015},
  "signals": {
    "sentence_length_match": true,
    "punctuation_style_match": true,
    "function_word_usage_match": true,
    "emoji_usage_match": true,
    "typo_rate_match": true,
    "vocabulary_richness_match": true
  }
}
```

---

## 🛰️ Level 2 — Infrastructure Attribution

Rather than treat persona-linking and real-world attribution as one blurred step, DeCypher
separates them explicitly:

- **Level 1** answers *"are these two accounts the same actor?"*
- **Level 2** answers *"does this actor's infrastructure point to a real server?"*

Level 2 runs four detectors against a target:

| Detector | What it looks for |
|---|---|
| `certificate.py` | SSL certificate fingerprint reuse between a hidden service and a clearnet domain |
| `status_page.py` | Exposed status/admin pages leaking real hostnames |
| `banner.py` | Default service banners matching known clearnet infrastructure |
| `descriptor_timing.py` | Tor descriptor timing anomalies |

Findings are posted to the backend as `Observation` records with a `confidence` score and
`source` tag, and appear directly in an actor's Evidence Trail alongside Level 1 signals.

**Safety note:** all scanning runs against an authorized, self-hosted mock hidden service —
never live marketplaces — every observation is tagged `source: authorized-test-service`.

---

## 📊 Dataset

DeCypher is built and demoed entirely on **ethically-sourced data**:

- **Stylometry validation:** PAN20 Authorship Verification (academic, published benchmark)
- **Graph correlation & demo:** a fully synthetic dataset — no real dark-web content, no
  real people, no real infrastructure — generated with realistic per-actor writing
  tendencies (not deterministic rules) so stylometric separation is genuine rather than
  trivially easy
- Ground-truth actor identity is retained only for scoring model accuracy, never fed to the
  model as a feature

---

## 📁 Project Structure

```
DeCypher/
├── backend/
│   ├── app/
│   │   ├── routers/        # auth, actors, search, feedback, export, scanner, nlp
│   │   ├── services/        # graph_service, ingestion, nlp_service
│   │   ├── middleware/        # audit_log
│   │   ├── models/             # sql_models, schemas
│   │   ├── database/            # postgres, neo4j_client
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/                    # pytest suite
│   ├── docker-compose.yml         # Postgres + Neo4j
│   └── requirements.txt
├── ai/nlp/
│   ├── compare_handles.py         # DeCypherAuthorshipEngine
│   └── models/                     # trained classifiers + vectorizers
├── infra/
│   ├── detectors/                   # banner, certificate, status_page, descriptor_timing
│   ├── scanner.py
│   ├── observation_mapper.py
│   └── backend_client.py
├── mock_service/                     # self-hosted target for safe Level 2 demos
├── frontend/
│   ├── src/
│   │   ├── pages/                     # LoginPage, SearchPage, GraphPage, ActorPage
│   │   └── api/client.ts
│   └── package.json
└── data/                                # synthetic dataset (actors, handles, wallets,
                                          # posts, marketplaces, infrastructure_indicators)
```

---

## ⚖️ Ethics & Legal Safeguards

- No live scraping of real dark web marketplaces — all data is academic (PAN20) or
  synthetic
- Level 2 infrastructure scanning targets only a self-hosted, authorized mock service
- Every attribution is framed as an **investigative lead**, never a confirmed identity —
  human-in-the-loop verdicts (`/feedback`) are part of the core workflow, not an afterthought
- Bulk export restricted to `admin` role; every request audit-logged with username, endpoint,
  and timestamp

---

## 🗺️ Roadmap

Designed for, not yet deployed in this prototype:

- [ ] Kafka/RabbitMQ event bus for scan-complete notifications
- [ ] Celery + Redis for fully autonomous, self-prioritizing rescanning
- [ ] Kubernetes deployment for horizontal scaling
- [ ] Grafana dashboards on top of the existing Prometheus metrics endpoint
- [ ] Formatted PDF report export (CSV/JSON export already implemented)
- [ ] Neo4j Graph Data Science-based cluster/community detection for organized-actor groups
- [ ] Cross-dataset domain adaptation to close the PAN20→PAN11 transfer gap

---

## 👥 Team DeCypher

Smart India Hackathon 2026 — Problem Statement 26151

- **[Your Name]** — Team Lead
- **[Member 2]** — Backend (FastAPI, Neo4j, PostgreSQL)
- **[Member 3]** — AI/NLP (stylometric attribution engine)
- **[Member 4]** — Infrastructure Attribution (Level 2 detectors)
- **[Member 5]** — Frontend (React, graph visualization)
- **[Member 6]** — Frontend / Integration

---

## 🙏 Acknowledgments

- **National Technical Research Organisation (NTRO)** — for the problem statement
- **PAN (Webis Group)** — for the Authorship Verification benchmark datasets
- **Smart India Hackathon 2026** — for the platform
- **Open Source Community** — FastAPI, Neo4j, PostgreSQL, React, scikit-learn

---

<div align="center">

**Built by Team DeCypher**
ADITYA KUMAR
HARSHIT BISLA
HIMANSHI
LOKESH YADAV
PARVESH
RYTHM VATS 

_Smart India Hackathon 2026 · Problem Statement 26151_

[⬆ Back to Top](#️-decypher--dark-web-threat-actor-de-anonymization-platform)

</div>
