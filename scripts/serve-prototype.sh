#!/usr/bin/env bash
# Run the prototype API (memory catalog unless DELPHI_DATABASE_URL is set).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
cd "$ROOT"
uv run --project delphi --with "$ROOT/daedalus" --with "$ROOT/prometheus" \
  python "$ROOT/scripts/serve_prototype.py" "$@"
