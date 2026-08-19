# daedalus

Ingestion pipeline for papers and (later) patents.

Treat this folder as if it were a standalone repository (`pirlruc/daedalus`). Depend on `contracts` only. Write into Delphi through its API or documented repository, not by importing Delphi internals.

## Role

Turn external records into Work nodes and citation edges.

Phase 1: public metadata only (OpenAlex slice), idempotent upserts, no LLM, no PDFs ([SYS-004](../docs/issues.yml), [PROTO-003](../docs/issues.yml)).

Phase 2: patent connectors ([PROD-001](../docs/issues.yml)), optional LLM extraction with backoff and DLQ ([PROD-002](../docs/issues.yml)), embeddings ([PROD-003](../docs/issues.yml)).

Phase 3: queued workers at throughput ([SCALE-002](../docs/issues.yml)).

## Layout (target, PROTO-003)

```
daedalus/
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock
  src/daedalus/
  tests/
  docs/ai-agent-handoff.md
```

## Status

Skeleton only.

## Commands (once the package exists)

```bash
cd daedalus
uv sync --frozen --extra dev
uv run pytest
```
