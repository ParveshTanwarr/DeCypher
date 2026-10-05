#!/usr/bin/env bash
set -euo pipefail

NO_FRONTEND=0
if [[ "${1:-}" == "--no-frontend" ]]; then
  NO_FRONTEND=1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
ENV_FILE="$BACKEND/.env"
ENV_EXAMPLE="$BACKEND/.env.example"

fail() { echo; echo "[ERROR] $1" >&2; exit 1; }
info() { echo "[*] $1"; }
pass() { echo "[OK] $1"; }

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or is not available on PATH."
docker info >/dev/null 2>&1 || fail "Docker is installed, but the Docker engine is not running."
docker compose version >/dev/null 2>&1 || fail "Docker Compose is not available through the Docker CLI."
pass "Docker and Docker Compose are available."

if [[ "$NO_FRONTEND" -eq 0 ]]; then
  command -v node >/dev/null 2>&1 || fail "Node.js is required for the frontend. Install Node.js 20.19+ or 22.12+."
  command -v npm >/dev/null 2>&1 || fail "npm is required for the frontend."
  NODE_VERSION="$(node --version | sed 's/^v//')"
  NODE_MAJOR="${NODE_VERSION%%.*}"
  NODE_REST="${NODE_VERSION#*.}"
  NODE_MINOR="${NODE_REST%%.*}"
  if [[ "$NODE_MAJOR" -lt 20 || ( "$NODE_MAJOR" -eq 20 && "$NODE_MINOR" -lt 19 ) ]]; then
    fail "Node.js $NODE_VERSION is too old. Install Node.js 20.19+ or 22.12+."
  fi
  pass "Node.js $NODE_VERSION and npm are available."
fi

[[ -f "$ENV_EXAMPLE" ]] || fail "Missing backend/.env.example."

random_hex() {
  local bytes="$1"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$bytes"
  else
    od -An -N "$bytes" -tx1 /dev/urandom | tr -d ' \n'
  fi
}

get_env() {
  local name="$1"
  grep -E "^${name}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true
}

set_env() {
  local name="$1"
  local value="$2"
  if grep -qE "^${name}=" "$ENV_FILE"; then
    sed -i.bak "s|^${name}=.*$|${name}=${value}|" "$ENV_FILE"
    rm -f "$ENV_FILE.bak"
  else
    printf '%s\n' "${name}=${value}" >> "$ENV_FILE"
  fi
}

repair_placeholder() {
  local name="$1"
  local generated="$2"
  shift 2
  local current
  current="$(get_env "$name")"
  if [[ -z "$current" ]]; then
    set_env "$name" "$generated"
    return
  fi
  for placeholder in "$@"; do
    if [[ "$current" == "$placeholder" ]]; then
      set_env "$name" "$generated"
      return
    fi
  done
}

if [[ -f "$ENV_FILE" ]]; then
  ENV_CREATED=0
else
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  ENV_CREATED=1
fi

POSTGRES_GENERATED="$(random_hex 24)"
NEO4J_GENERATED="$(random_hex 24)"
GRAFANA_GENERATED="$(random_hex 24)"
SECRET_GENERATED="$(random_hex 32)"
ADMIN_GENERATED="$(random_hex 12)"
ANALYST_GENERATED="$(random_hex 12)"
SCANNER_GENERATED="$(random_hex 12)"

repair_placeholder POSTGRES_PASSWORD "$POSTGRES_GENERATED" "change-this-in-local-env"
repair_placeholder NEO4J_PASSWORD "$NEO4J_GENERATED" "change-this-neo4j-password" "change-this-in-local-env"
repair_placeholder GRAFANA_ADMIN_PASSWORD "$GRAFANA_GENERATED" "change-this-in-local-env"
repair_placeholder SECRET_KEY "$SECRET_GENERATED" "replace-with-a-unique-random-secret"
repair_placeholder ADMIN_PASSWORD "$ADMIN_GENERATED" "replace-with-a-strong-admin-password"
repair_placeholder ANALYST_PASSWORD "$ANALYST_GENERATED" "replace-with-a-strong-investigator-password"
repair_placeholder SCANNER_SERVICE_PASSWORD "$SCANNER_GENERATED" "replace-with-a-strong-service-password"

POSTGRES_PASSWORD="$(get_env POSTGRES_PASSWORD)"
DATABASE_URL="$(get_env DATABASE_URL)"
if [[ -z "$DATABASE_URL" || "$DATABASE_URL" == *"change-this-in-local-env"* ]]; then
  set_env DATABASE_URL "postgresql+psycopg2://postgres:${POSTGRES_PASSWORD}@127.0.0.1:5433/threat_intel"
fi

set_env DEMO_MODE true
set_env DEMO_DATASET_VERSION 2026-10-05-v1
set_env DEMO_REFERENCE_DATE 2026-10-05
set_env AUTOSCAN_ENABLED false
set_env COLLECTION_ENABLED false

ADMIN_PASSWORD="$(get_env ADMIN_PASSWORD)"
ANALYST_PASSWORD="$(get_env ANALYST_PASSWORD)"
NEO4J_PASSWORD="$(get_env NEO4J_PASSWORD)"
GRAFANA_PASSWORD="$(get_env GRAFANA_ADMIN_PASSWORD)"
SCANNER_PASSWORD="$(get_env SCANNER_SERVICE_PASSWORD)"
SECRET_KEY="$(get_env SECRET_KEY)"

[[ -n "$POSTGRES_PASSWORD" && -n "$NEO4J_PASSWORD" && -n "$GRAFANA_PASSWORD" && -n "$SECRET_KEY" && -n "$ADMIN_PASSWORD" && -n "$ANALYST_PASSWORD" && -n "$SCANNER_PASSWORD" ]] || fail "backend/.env is missing required credentials."

if [[ "$ENV_CREATED" -eq 1 ]]; then
  pass "Created backend/.env with local-only generated credentials."
else
  pass "Existing backend/.env preserved; known template placeholders were repaired."
fi

info "Starting backend services..."
cd "$BACKEND"
docker compose up -d --build || {
  docker compose ps || true
  fail "Docker Compose failed to start."
}

DEADLINE=$((SECONDS + 300))
HEALTHY=0
while (( SECONDS < DEADLINE )); do
  HEALTH="$(curl -fsS --max-time 5 http://127.0.0.1:8000/health 2>/dev/null || true)"
  if [[ "$HEALTH" == *'"status":"healthy"'* || "$HEALTH" == *'"status": "healthy"'* ]]; then
    HEALTHY=1
    break
  fi
  sleep 5
done

if [[ "$HEALTHY" -ne 1 ]]; then
  docker compose ps || true
  echo
  docker compose logs --tail=100 api || true
  fail "API did not become dependency-healthy within 5 minutes."
fi
pass "PostgreSQL, Redis, Neo4j and API readiness checks passed."

if [[ "$NO_FRONTEND" -eq 0 ]]; then
  cd "$FRONTEND"
  if [[ ! -d node_modules ]]; then
    info "Installing frontend dependencies with npm ci..."
    npm ci
  else
    pass "Frontend dependencies already installed."
  fi

  echo
  echo "========================================"
  echo " DeCypher Demo Ready"
  echo "========================================"
  echo "Frontend : http://localhost:5173"
  echo "API      : http://127.0.0.1:8000"
  echo "API docs : http://127.0.0.1:8000/docs"
  echo
  echo "Login credentials"
  echo "  admin   : $ADMIN_PASSWORD"
  echo "  analyst : $ANALYST_PASSWORD"
  echo
  echo "Generated backend/.env is local-only and must not be committed."
  echo "Press Ctrl+C to stop Vite. Docker services remain running."
  echo "========================================"
  echo

  exec npm run dev -- --host 127.0.0.1
else
  echo
  echo "DeCypher backend is ready."
  echo "API: http://127.0.0.1:8000"
  echo "API docs: http://127.0.0.1:8000/docs"
  echo "admin: $ADMIN_PASSWORD"
  echo "analyst: $ANALYST_PASSWORD"
fi
