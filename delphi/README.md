# delphi

Centralized catalog and query API.

Treat this folder as if it were a standalone repository (`pirlruc/delphi`). Depend on `contracts` only. Do not import Daedalus, Prometheus, Epimetheus, or Hermes source.

## Role

Serve batch identifier checks, consented PDF accept, and dated citation neighborhoods. Expose generate (`research_path` or `patent_whitespace`) filtered by category/subcategory. Delphi is **not** the ingest pipeline, **not** the path generator, and **not** the judge.

Prototype persistence is Postgres 16 + pgvector behind repository interfaces ([SYS-002](../docs/issues.yml)). Distributed graph and vector engines wait for [SCALE-001](../docs/issues.yml).

## Layout (target, PROTO-002)

```
delphi/
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock
  src/delphi/
  tests/
  docs/ai-agent-handoff.md
```

## Status

Skeleton only. Implementation is [PROTO-002](../docs/issues.yml). REST only in Phase 1.

## Commands (once the package exists)

```bash
cd delphi
uv sync --frozen --extra dev
uv run pytest
```
