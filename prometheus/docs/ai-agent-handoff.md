# AI Agent Handoff — prometheus

Generator only. If this package starts fetching from Delphi, that is a leak vector for hindcasting.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. No generator yet ([PROTO-004](../../docs/issues.yml)).

## Constraints

- Input is `MaskedContext`. Tests must fail if future work ids are present.
- LLM provider is an interface with a deterministic fake ([PY-PERF-002](https://github.com/pirlruc/guardrails/blob/1.3.0/python/guardrails.md)).
- Prompts must instruct the model not to use knowledge after the mask date; that is necessary but not sufficient — the mask itself is the control.

## Suggested next work

PROTO-004-T1 after contracts define PathRequest/Response.
