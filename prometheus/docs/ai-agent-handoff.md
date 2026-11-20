# AI Agent Handoff — prometheus

Generator only. If this package starts fetching from Delphi, that is a leak vector for hindcasting.

**Last updated:** 2026-08-19

## Current slice

Walking skeleton ([PROTO-004](../../docs/issues.yml)). Import name `delphi_prometheus`. `PathGenerator` takes a `MaskedContext` and the SYS-006 provider (Fake in tests).

## Constraints

- Must not fetch from Delphi. Input is `MaskedContext` built by Epimetheus (or by Delphi for live queries). That context includes **both** citation and content neighborhoods ([SYS-010](../../docs/issues.yml)).
- Tests must fail if future work ids are **present** in the neighborhood. A held-out id that was already dropped from neighbors is metadata, not a leak.
- LLM provider is SYS-006 (Fake / cloud / local OpenAI-compatible). Tests must not need a GPU or API key.
- Output kind is `research_path` or `patent_whitespace`.
- Prompts must instruct the model not to use knowledge after the mask date; that is necessary but not sufficient — the mask itself is the control.

## Suggested next work

Richer prompts and structured-output validation once a non-Fake provider is used in a live hindcast ([PROTO-007](../../docs/issues.yml)).
