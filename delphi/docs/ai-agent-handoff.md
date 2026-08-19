# AI Agent Handoff — delphi

Catalog and query service. Hide SQL behind repository interfaces so SCALE-001 can swap engines.

**Last updated:** 2026-08-19

## Current slice

Walking skeleton ([PROTO-002](../../docs/issues.yml)). FastAPI app with `MemoryCatalog`: `POST /v1/works:batch-check`, `GET /v1/works/{id}/neighborhood`, `POST /v1/uploads`, `POST /v1/generate`. Extractor/embedder/generator are ports so this package does not import siblings. Default `scripts/serve_prototype.py` wires Daedalus + Prometheus at the composition root.

Postgres/pgvector is in root `docker-compose.yml` and is **not** the default serve backend yet.

## Constraints

- Batch-check must not require PDF bytes ([SYS-003](../../docs/issues.yml)).
- PDF accept is a separate consented endpoint ([SYS-004](../../docs/issues.yml)).
- Generate requires kind plus category/subcategory ([SYS-007](../../docs/issues.yml), [SYS-008](../../docs/issues.yml)).
- Neighborhood queries return citation, content, or union modes ([SYS-010](../../docs/issues.yml)). Content neighbors are other works, not the PDF in isolation.
- Must not parse PDFs or call OpenAlex (Daedalus), invent paths from an unmasked catalog (Prometheus), or compute hindcast metrics (Epimetheus).
- GraphQL is out of scope until SCALE-001 says Hermes query shapes need it.
- Python 3.13 / uv / PY-* floors.

## Suggested next work

Wire `MemoryCatalog` to Postgres/pgvector without changing the REST contract ([PROTO-002](../../docs/issues.yml) remaining acceptance, [SYS-002](../../docs/issues.yml)).
