# AI Agent Handoff — epimetheus

Eval harness. Sacred constraint: no look-ahead in the context window.

**Last updated:** 2026-08-19

## Current slice

Walking skeleton ([PROTO-005](../../docs/issues.yml)). Masks drop held-out works, later dates, citation descendants, and later `similar_to` neighbors. CLI writes an `EvalRun` JSON artifact using the Fake judge.

## Constraints

- Unit-test leak fixtures before any live LLM judge ([PROTO-005-T1](../../docs/issues.yml)).
- Must not see catalog rows with publication date after the cut, citation descendants of those rows, or content-graph neighbors that only exist because of later papers ([SYS-010](../../docs/issues.yml)).
- Judge and any live calls use SYS-006 (Fake / cloud / local). EvalRun stores adapter + model id.
- Prometheus must not be allowed to "helpfully" refetch the catalog during an eval run.
- Package `src` must not import `delphi` or `daedalus`.

## Suggested next work

Run hindcasts against the ingested slice (not only the tiny CLI fixture) and record mean scores for [PROTO-007](../../docs/issues.yml).
