# AI Agent Handoff — contracts

Isolated schema package. Do not import sibling component trees.

**Last updated:** 2026-08-19

## Current slice

README + this handoff. No Python package yet ([PROTO-001](../../docs/issues.yml)).

## Constraints

- Python 3.13, uv, Google docstrings ([PY-RUN-001](https://github.com/pirlruc/guardrails/blob/1.3.0/python/guardrails.md), [PY-DOC-002](https://github.com/pirlruc/guardrails/blob/1.3.0/python/guardrails.md)).
- Public model changes need migration notes ([PY-API-001](https://github.com/pirlruc/guardrails/blob/1.3.0/python/guardrails.md)).
- Identity fields are decided in [SYS-003](../../docs/issues.yml): UUID plus DOI / arXiv / OpenAlex / patent / content hash.
- Category schemes: `openalex_topic` and `cpc` ([SYS-008](../../docs/issues.yml)).
- PathRequest.kind: `research_path` or `patent_whitespace` ([SYS-007](../../docs/issues.yml)).

## Suggested next work

PROTO-001-T1: package skeleton and batch-check models.
