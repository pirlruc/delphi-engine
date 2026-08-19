# prometheus

Research-path and patent-whitespace **generator**.

Treat this folder as if it were a standalone repository (`pirlruc/prometheus`). Depend on `contracts` only. Do not query Delphi; callers pass a `MaskedContext`.

## Role

Given a seed and a past-only neighborhood, propose ranked next steps (methods, combinations, gaps) that cite only context works. This is the product brain. Epimetheus scores it; Hermes displays it; Delphi does not call an LLM on every query unless a caller asks.

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
