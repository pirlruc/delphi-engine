# AI Agent Handoff — contracts

Isolated schema package. Do not import sibling component trees.

**Last updated:** 2026-08-19

## Current slice

Walking skeleton ([PROTO-001](../../docs/issues.yml)). Package `delphi_contracts` exports identity, extraction, neighborhood, path, eval, and SYS-006 LLM models. OpenAPI is at `src/delphi_contracts/openapi.json`.

## Constraints

- Python 3.13, uv, Google docstrings ([PY-RUN-001](https://github.com/pirlruc/guardrails/blob/1.15.0/python/guardrails.md), [PY-DOC-002](https://github.com/pirlruc/guardrails/blob/1.15.0/python/guardrails.md)).
- Public model changes need migration notes ([PY-API-001](https://github.com/pirlruc/guardrails/blob/1.15.0/python/guardrails.md)).
- Identity fields are decided in [SYS-003](../../docs/issues.yml): UUID plus DOI / arXiv / OpenAlex / patent / content hash.
- Category schemes: `openalex_topic` and `cpc` ([SYS-008](../../docs/issues.yml)).
- PathRequest.kind: `research_path` or `patent_whitespace` ([SYS-007](../../docs/issues.yml)).
- Extraction covers title, authors, keywords, bibliography, and body text. Neighborhood modes are `citation`, `content`, and `union` ([SYS-010](../../docs/issues.yml)).
- `MaskedContext.forbidden_ids()` only flags held-out ids that are **present** in the seed or neighbors, plus neighbors published after `mask_on`.

## Suggested next work

Keep models frozen unless a later Epic requires a field. Consumers install this package as an editable path dependency.
