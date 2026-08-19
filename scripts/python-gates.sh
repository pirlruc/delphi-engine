#!/usr/bin/env bash
# PY-* local gates for every Python package (CI-008 companion).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
PACKAGES=(contracts delphi daedalus prometheus epimetheus hermes)
for pkg in "${PACKAGES[@]}"; do
  echo "==> ${pkg}"
  cd "${ROOT}/${pkg}"
  uv sync --extra dev
  uv run ruff check src tests
  uv run ruff format --check src tests
  uv run mypy src
  uv run interrogate src
  uv run pytest
done
echo "python-gates: ok"
