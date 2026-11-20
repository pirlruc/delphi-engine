# prometheus

Research-path and patent-whitespace **generator**.

Treat this folder as if it were a standalone repository (`pirlruc/prometheus`). Depend on `contracts` only. Do not query Delphi; callers pass a `MaskedContext`.

## Role

Given a seed (catalog work or extracted PDF) and a past-only neighborhood filtered by category/subcategory, propose ranked next steps. The neighborhood includes **citation** neighbors and **content** neighbors (other papers with similar text), tagged by edge kind.

`PathRequest.kind` is `research_path` or `patent_whitespace`. This is the product brain. Epimetheus scores it; Hermes displays it.

LLM calls go through the SYS-006 provider: Fake in tests, cloud or local OpenAI-compatible (Ollama, vLLM) in live runs. Switching adapter is config, not a rewrite.

The name pairs with Epimetheus: forethought versus hindsight.

The Python import name is `delphi_prometheus` so it does not clash with the Prometheus metrics client.

## Layout

```
prometheus/
  README.md
  CHANGELOG.md
  pyproject.toml
  src/delphi_prometheus/
  tests/
  docs/ai-agent-handoff.md
```

## Status

Walking skeleton ([PROTO-004](../docs/issues.yml)). `PathGenerator.generate` refuses a context whose **present** works include a held-out or future id.

## Commands

```bash
cd prometheus
uv sync --frozen --extra dev
uv run pytest
```
