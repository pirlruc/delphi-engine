# AI Agent Handoff — delphi

Catalog and query service. Hide SQL behind repository interfaces so SCALE-001 can swap engines.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. No FastAPI app yet ([PROTO-002](../../docs/issues.yml)).

## Constraints

- Batch-check must not require PDF bytes ([SYS-003](../../docs/issues.yml), [SYS-004](../../docs/issues.yml)).
- GraphQL is out of scope until SCALE-001 says Hermes query shapes need it.
- Python 3.13 / uv / PY-* floors once code exists.

## Suggested next work

PROTO-001 (contracts) then PROTO-002-T1 (batch-check + neighborhood).
