# delphi

Centralized catalog and query API.

Treat this folder as if it were a standalone repository (`pirlruc/delphi`). Depend on `contracts` only. Do not import Daedalus, Prometheus, Epimetheus, or Hermes source.

## Role

Serve batch identifier checks, consented PDF accept, and dual neighborhoods: **citation** (`cites`) and **content** (`similar_to` from embeddings of this work versus other works). Expose generate (`research_path` or `patent_whitespace`) filtered by category/subcategory. Delphi is **not** the ingest pipeline, **not** the path generator, and **not** the judge.

Prototype persistence is `MemoryCatalog` unless `DELPHI_DATABASE_URL` is set, which selects `PostgresCatalog` (works, identities, cites, similar_to, embeddings, extractions in one Postgres 16 database). Compose starts API plus Postgres ([SYS-002](../docs/issues.yml)). Graph rules: [`docs/prototype-graphs.md`](../docs/prototype-graphs.md). Distributed graph and vector engines wait for [SCALE-001](../docs/issues.yml).

## Layout

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

Walking skeleton ([PROTO-002](../docs/issues.yml)). REST only. Collaborators (extractor, embedder, generator) are injected so this package does not import siblings.

## Commands

```bash
cd delphi
uv sync --frozen --extra dev
uv run pytest
```

Run the composition root from the workspace:

```bash
bash scripts/serve-prototype.sh
# or: docker compose up --build
```
