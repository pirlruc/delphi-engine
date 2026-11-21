#!/usr/bin/env bash
# Local CI parity (CI-008). Same checks as .github/workflows/quality.yml.
# Does not call GitHub Actions and does not clone private analog remotes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 .github/scaffold/scripts/issues-sync.py --yaml docs/issues.yml --validate-only

python3 - <<'PY'
from pathlib import Path
import yaml

paths = [
    Path("docs/issues.yml"),
    Path("docs/issues-sync-targets.yml"),
    Path("docs/guardrail-deviations.yml"),
    Path(".github/dependabot.yml"),
    Path(".github/workflows/quality.yml"),
]
for path in paths:
    yaml.safe_load(path.read_text(encoding="utf-8"))
    print(f"ok {path}")
PY

echo "check-ci-local: ok"

if [[ "${SKIP_PYTHON_GATES:-}" != "1" ]]; then
	bash "$ROOT/scripts/python-gates.sh"
fi
