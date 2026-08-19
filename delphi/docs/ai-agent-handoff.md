# AI Agent Handoff — delphi

Catalog and query service. Hide SQL behind repository interfaces so SCALE-001 can swap engines.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. No FastAPI app yet ([PROTO-002](../../docs/issues.yml)).

## Constraints

- Batch-check must not require PDF bytes ([SYS-003](../../docs/issues.yml)).
- PDF accept is a separate consented endpoint ([SYS-004](../../docs/issues.yml)).
- Generate requires kind plus category/subcategory ([SYS-007](../../docs/issues.yml), [SYS-008](../../docs/issues.yml)).
- Neighborhood queries return citation, content, or union modes ([SYS-010](../../docs/issues.yml)). Content neighbors are other works, not the PDF in isolation.
- Must not parse PDFs or call OpenAlex (Daedalus), invent paths from an unmasked catalog (Prometheus), or compute hindcast metrics (Epimetheus).
- GraphQL is out of scope until SCALE-001 says Hermes query shapes need it.
- Python 3.13 / uv / PY-* floors once code exists.

## Suggested next work

PROTO-001 (contracts) then PROTO-002-T1 (batch-check + citation/content neighborhood).
