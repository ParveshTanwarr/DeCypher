# Contributing

## Development environment

The supported development layout is repository-local; the directory name on your computer does not matter to Git.

### Backend

From the repository root:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
pytest -q
```

### Frontend

In a second terminal:

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

The backend and frontend commands above are also the core CI validation steps.

## Before submitting a change

Run:

```powershell
cd backend
pytest -q

cd ..\frontend
npm run lint
npm run build
```

Keep changes focused. If a change affects scoring, correlation, authentication, scanner behavior, database models, or exports, add or update regression tests.

## Pull requests

Describe:

- what changed
- why it changed
- tests run
- any known limitations

Avoid committing generated files such as `.venv`, `node_modules`, caches, build output, or local environment files.
