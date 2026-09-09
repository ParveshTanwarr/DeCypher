# DeCypher

## SIH Project — Dark Web Threat Actor De-anonymization

DeCypher is an evidence-correlation platform for investigator-assisted threat-actor attribution. It correlates reusable technical, financial, behavioral, temporal, and linguistic artifacts and presents the resulting relationships through an investigation dashboard and graph view.

### Core components

- `frontend/` — React/Vite investigation dashboard
- `backend/` — FastAPI API, authentication, correlation and data services
- `ai/` — NLP/authorship inference models and integration
- `data/` — synthetic actors, handles, posts, wallets and infrastructure indicators
- `graph/` — Neo4j graph-related components
- `infra/` — controlled infrastructure scanner
- `mock_service/` — controlled test service used for authorized scanner demonstrations
- `tests/` — project tests

### Evidence signals

- Wallet reuse
- Infrastructure reuse
- TLS certificate reuse
- Banner matching
- Descriptor timing
- Stylometric similarity

The platform produces explainable correlation and operational triage scores. These scores are intended to assist investigators and do not represent proof or a probability of real-world identity.

## SIH repository structure

Submission material is organized according to the SIH reference repository structure:

```text
DeCypher/
├── README.md
├── SUBMISSION_GUIDE.md
├── submission/
│   ├── PRESENTATION.md
│   └── DEMO.md
├── src/
│   └── main.py
├── docs/
│   └── architecture.md
├── assets/
│   └── screenshots/
│       └── README.md
├── requirements.txt
├── .gitignore
└── LICENSE
```

The existing application directories remain alongside this submission structure because they contain the working DeCypher implementation.

## Data safety

The repository's demonstration data is synthetic and intended for controlled development and demonstration. Do not use the platform to target systems without authorization.
