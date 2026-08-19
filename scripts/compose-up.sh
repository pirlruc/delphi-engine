#!/usr/bin/env bash
# Bring up Postgres 16 + Delphi API. Requires Docker Compose on the host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "wrote .env from .env.example (edit credentials, then re-run)"
fi
docker compose up --build "$@"
