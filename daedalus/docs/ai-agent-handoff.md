# AI Agent Handoff — daedalus

Ingest only. Do not score paths or serve HTTP to Hermes.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. No connectors yet ([PROTO-003](../../docs/issues.yml)).

## Constraints

- Prototype source is OpenAlex metadata. No raw PDF ingest in Phase 1 ([SYS-004](../../docs/issues.yml)).
- Default slice is computer-science / ML unless the owner names another field.
- LLM extraction is PROD-002, not a prerequisite for hindcasting.

## Suggested next work

PROTO-003-T1 after Delphi can upsert works and edges.
