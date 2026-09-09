# SIH 2026 Submission Guide

This repository follows the requested SIH 2026 submission-oriented structure.

## Repository structure

```text
YOUR-SIH-PROJECT/
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

### What goes where?

| Item | Location |
|---|---|
| Source code | `src/` or the project's normal source folders |
| Architecture / technical documentation | `docs/` |
| Project screenshots / hardware photos | `assets/screenshots/` |
| Final PPT / presentation | `submission/` |
| Demo video link | `submission/DEMO.md` |
| Project overview | `README.md` |

## Submission material

- Keep the final presentation in `submission/` when the file size permits.
- Put the accessible demo-video link in `submission/DEMO.md`.
- Store important project screenshots in `assets/screenshots/`.
- Keep the repository accessible to reviewers before submission.
- Do not commit passwords, API keys, access tokens, `.env` files containing secrets, or other confidential credentials.

## DeCypher note

DeCypher has an existing multi-component implementation (`backend/`, `frontend/`, `ai/`, `data/`, `graph/`, `infra/`, `mock_service/`, and `tests/`). These directories are intentionally retained rather than moved into `src/`, so the working application and its runtime paths are not disrupted.
