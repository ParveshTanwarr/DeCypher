# DeCypher frontend

React + TypeScript + Vite frontend for the DeCypher threat-intelligence demonstration platform.

## Prerequisites

- Node.js 20.19+ or 22.12+
- npm
- A running DeCypher backend at the API URL configured by the frontend API client

## Install and run

From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server normally starts at:

```
http://localhost:5173
```

## Validate the frontend

Run the linter:

```powershell
npm run lint
```

Run the production build:

```powershell
npm run build
```

Preview the production build locally:

```powershell
npm run preview
```

CI uses `npm ci` so the committed `package-lock.json` is the reproducible dependency source for automated builds.

## Typical local workflow

Start the backend first:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Then, in a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173` and sign in with the development credentials documented in the root README.

## Project structure

```text
frontend/
├── src/
│   ├── api/           # backend API client
│   ├── components/    # reusable UI components
│   └── pages/         # investigation views
├── public/
├── package.json
└── package-lock.json
```

The frontend is a controlled demonstration UI. It does not contain the Gemini API credential; optional Gemini access is handled by the backend.
