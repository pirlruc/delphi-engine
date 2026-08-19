# AI Agent Handoff — epimetheus

Eval harness. Sacred constraint: no look-ahead in the context window.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. No mask implementation yet ([PROTO-005](../../docs/issues.yml)).

## Constraints

- Unit-test leak fixtures before any live LLM judge ([PROTO-005-T1](../../docs/issues.yml)).
- Judge and any live calls use SYS-006 (Fake / cloud / local). EvalRun stores adapter + model id.
- Prometheus must not be allowed to "helpfully" refetch the catalog during an eval run.

## Suggested next work

PROTO-005-T1 leak tests on a fixture graph, then T2 judge artifact.
