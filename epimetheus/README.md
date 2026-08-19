# epimetheus

Hindcasting evaluation harness.

Treat this folder as if it were a standalone repository (`pirlruc/epimetheus`). Depend on `contracts`. Call Prometheus with a context you built. Read the catalog through Delphi's API, not by importing Delphi internals.

## Role

1. Pick a historical work.
2. Build a temporal mask: drop that work, every later work, and the downstream citation closure.
3. Ask Prometheus to propose the next step from the remaining past.
4. Score the proposal against the held-out work (LLM-as-judge plus embedding similarity).

If a future paper can reach the prompt, the run is invalid. That rule is stricter than model quality.

Phase 1 is a batch CLI plus JSON metrics ([PROTO-005](../docs/issues.yml), [PROTO-007](../docs/issues.yml)). Human review is [PROD-006](../docs/issues.yml), not a second desktop app.

## Layout (target, PROTO-005)

```
epimetheus/
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock
  src/epimetheus/
  tests/
  docs/ai-agent-handoff.md
```

## Status

Skeleton only.

## Commands (once the package exists)

```bash
cd epimetheus
uv sync --frozen --extra dev
uv run pytest
```
