# daedalus

Ingestion pipeline for papers, patents, and consented user PDFs.

Treat this folder as if it were a standalone repository (`pirlruc/daedalus`). Depend on `contracts` only. Write into Delphi through its API or documented repository, not by importing Delphi internals. Tests may use `MemoryCatalog` via a **dev** extra.

## Role

Turn external records and uploaded PDFs into Work nodes, `cites` edges, `similar_to` edges, embeddings, and categories.

Phase 1 walking skeleton: packaged SYS-009 fixture (papers + one patent), OpenAlex/PatentsView **mappers** (live API shape plus simplified fixtures), PDF extraction of title, authors, keywords, bibliography, and body ([PROTO-008](../docs/issues.yml)), and composed embeddings vs other papers ([PROTO-009](../docs/issues.yml), [evolution.md](../docs/evolution.md)). Live OpenAlex paging: `uv run daedalus --live --per-subcategory 5`. Patent offices: `uv run daedalus --live-patents` (EPO OPS, WIPO JSON gateway, PatSnap, Lens.org; skip if credentials unset). Tens-of-thousands ingest remains [PROTO-003](../docs/issues.yml). LLM calls use the SYS-006 provider (Fake / cloud / local OpenAI-compatible such as Ollama or vLLM).

Phase 2: wider patent coverage ([PROD-001](../docs/issues.yml)), queued extraction with DLQ ([PROD-002](../docs/issues.yml)), richer catalog text for re-embed ([PROD-003](../docs/issues.yml)).

Phase 3: workers at throughput ([SCALE-002](../docs/issues.yml)).

## Layout

```
daedalus/
  README.md
  CHANGELOG.md
  pyproject.toml
  src/daedalus/
  tests/
  docs/ai-agent-handoff.md
```

## Status

Walking skeleton. Ingest applies SYS-009 subcategory caps (transformers cannot exceed the other three combined; no medical/AV vision unless a later Epic adds them). Default catalog for the demo is the eight-work fixture in `src/daedalus/fixtures/slice.json`.

## Commands

```bash
cd daedalus
uv sync --frozen --extra dev
uv run pytest
uv run daedalus --dry-run
# Live OpenAlex (four subcategories, small cap):
# uv run daedalus --live --per-subcategory 5 --output /tmp/oa-slice.json
# Live patents (skips sources without env credentials):
# uv run daedalus --live-patents --per-subcategory 5 --output /tmp/patent-slice.json
# HTTP page fetch (inject URL; retries + poison skip):
# uv run daedalus --openalex-url 'https://api.openalex.org/works?search=QR&per_page=5'
```
