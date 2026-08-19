# AI Agent Handoff — daedalus

Ingest and extraction only. Do not score paths or serve HTTP to Hermes.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. Catalog ingest is [PROTO-003](../../docs/issues.yml) against [SYS-009](../../docs/issues.yml) filters. PDF extraction is [PROTO-008](../../docs/issues.yml).

## Constraints

- Prototype sources: OpenAlex + CPC slice for transformers/FMs, bounded CV, steganography, 2D codes, plus consented user PDFs ([SYS-004](../../docs/issues.yml), [SYS-009](../../docs/issues.yml)).
- LLM extraction uses SYS-006 adapters (Fake in tests; cloud or local/Ollama/vLLM in live runs).
- Suggested categories use `openalex_topic` and `cpc` ([SYS-008](../../docs/issues.yml)).

## Suggested next work

SYS-009 filters are locked. PROTO-003-T1 and PROTO-008-T1 after Delphi can upsert.
