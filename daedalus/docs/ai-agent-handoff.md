# AI Agent Handoff — daedalus

Ingest and extraction only. Do not score paths or serve HTTP to Hermes.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. Blocked on [SYS-009](../../docs/issues.yml) for catalog ingest. PDF extraction is [PROTO-008](../../docs/issues.yml).

## Constraints

- Prototype sources: OpenAlex metadata + CPC patent slice of the named field, plus consented user PDFs ([SYS-004](../../docs/issues.yml)).
- LLM extraction uses SYS-006 adapters (Fake in tests; cloud or local/Ollama/vLLM in live runs).
- Suggested categories use `openalex_topic` and `cpc` ([SYS-008](../../docs/issues.yml)).

## Suggested next work

SYS-009 field name, then PROTO-003-T1 and PROTO-008-T1.
