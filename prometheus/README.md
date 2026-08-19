# prometheus

Research-path and patent-whitespace **generator**.

Treat this folder as if it were a standalone repository (`pirlruc/prometheus`). Depend on `contracts` only. Do not query Delphi; callers pass a `MaskedContext`.

## Role

Given a seed (catalog work or extracted PDF) and a past-only neighborhood filtered by category/subcategory, propose ranked next steps.

`PathRequest.kind` is `research_path` or `patent_whitespace`. This is the product brain. Epimetheus scores it; Hermes displays it.

LLM calls go through the SYS-006 provider: Fake in tests, cloud or local OpenAI-compatible (Ollama, vLLM) in live runs. Switching adapter is config, not a rewrite.

The name pairs with Epimetheus: forethought versus hindsight.

## Layout (target, PROTO-004)

```
prometheus/
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock
  src/prometheus/
  tests/
  docs/ai-agent-handoff.md
```

Package import name may be `delphi_prometheus` if `prometheus` clashes with the metrics client. Decide in PROTO-004-T1.

## Status

Skeleton only.

## Commands (once the package exists)

```bash
cd prometheus
uv sync --frozen --extra dev
uv run pytest
```
