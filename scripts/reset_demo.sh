#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [[ "${1:-}" != "--yes" ]]; then
  echo
  echo "WARNING: this removes the local DeCypher Docker volumes."
  echo "It deletes local PostgreSQL, Neo4j, Prometheus and Grafana demo state."
  echo "Do NOT use this if you need to preserve local investigation data."
  read -r -p "Type RESET to continue: " ANSWER
  if [[ "$ANSWER" != "RESET" ]]; then
    echo "Reset cancelled."
    exit 0
  fi
fi

cd "$BACKEND"
docker compose down -v

echo
echo "Demo volumes removed. Starting a fresh deterministic demo..."
bash "$ROOT/scripts/start_demo.sh"
