# daedalus

Ingestion pipeline for papers, patents, and consented user PDFs.

Treat this folder as if it were a standalone repository (`pirlruc/daedalus`). Depend on `contracts` only. Write into Delphi through its API or documented repository, not by importing Delphi internals.

## Role

Turn external records and uploaded PDFs into Work nodes, citation edges, extractions, and categories.

Phase 1: public metadata for the **named** field — OpenAlex papers plus a matching PatentsView/CPC slice ([PROTO-003](../docs/issues.yml), blocked on [SYS-009](../docs/issues.yml)) — and PDF extraction via the SYS-006 provider (Fake / cloud / local OpenAI-compatible such as Ollama or vLLM) ([PROTO-008](../docs/issues.yml)).

Phase 2: wider patent coverage ([PROD-001](../docs/issues.yml)), queued extraction with DLQ ([PROD-002](../docs/issues.yml)), embeddings ([PROD-003](../docs/issues.yml)).

Phase 3: workers at throughput ([SCALE-002](../docs/issues.yml)).

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

Skeleton only. Ingest must apply SYS-009 subcategory caps (transformers cannot exceed the other three combined; no medical/AV vision unless a later Epic adds them).

## Commands (once the package exists)

```bash
cd daedalus
uv sync --frozen --extra dev
uv run pytest
```
