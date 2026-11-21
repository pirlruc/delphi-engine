#!/usr/bin/env bash
# PROTO-007 demo: sample PDF upload, dual graphs, both generate kinds, slice hindcast.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
cd "$ROOT"
uv run --project daedalus --with "$ROOT/delphi" --with "$ROOT/prometheus" --with "$ROOT/epimetheus" \
	python "$ROOT/scripts/demo_prototype.py" "$@"
