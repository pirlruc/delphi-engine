# AI Agent Handoff — daedalus

Ingest and extraction only. Do not score paths or serve HTTP to Hermes.

**Last updated:** 2026-08-19

## Current slice

Walking skeleton. Fixture ingest for the SYS-009 slice ([PROTO-003-T1](../../docs/issues.yml)), PDF extraction ([PROTO-008](../../docs/issues.yml)), hash embeddings vs other papers ([PROTO-009](../../docs/issues.yml)). OpenAlex/PatentsView **HTTP** ingest is not live yet; mappers exist in `connectors.py`.

Package `src` must not import `delphi`. Tests use `MemoryCatalog` via the dev extra. Composition root is `scripts/serve_prototype.py`.

## Constraints

- Prototype sources: OpenAlex + CPC slice for transformers/FMs, bounded CV, steganography, 2D codes, plus consented user PDFs ([SYS-004](../../docs/issues.yml), [SYS-009](../../docs/issues.yml)).
- LLM extraction uses SYS-006 adapters (Fake in tests; cloud or local/Ollama/vLLM in live runs).
- Suggested categories use `openalex_topic` and `cpc` ([SYS-008](../../docs/issues.yml)).
- Must extract upload metadata and bibliography ([PROTO-008](../../docs/issues.yml)) and embed that text against **other** ingested works ([PROTO-009](../../docs/issues.yml), [SYS-010](../../docs/issues.yml)).
- Must not generate research paths (Prometheus), expose query HTTP (Delphi), or run hindcast scoring (Epimetheus).

## Suggested next work

Live OpenAlex/PatentsView page fetch with retries ([PROTO-003](../../docs/issues.yml) remaining).
