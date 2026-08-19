# hermes

Local research hub (client).

Treat this folder as if it were a standalone repository (`pirlruc/hermes`). Depend on `contracts`. Talk to Delphi over HTTP. Never import server internals.

## Role

Let a researcher overlay their library on the global catalog, then inspect AI-generated paths and whitespaces.

**Phase 1 ([PROTO-006](../docs/issues.yml)):** Python CLI + local SQLite cache. Batch-check identifiers from a file. Print a generated path. No PDF upload command.

**Phase 2 ([PROD-004](../docs/issues.yml)):** Tauri + React desktop. First reference manager is local Zotero SQLite. Prompt before any raw PDF upload. Qiqqa and Mendeley wait until Zotero works.

There is no TypeScript guardrails pack in pirlruc/guardrails today. Desktop quality gates must be decided on PROD-004 (record a deviation or extract Hermes). The Phase 1 CLI stays on PY-*.

## Layout (Phase 1)

```
hermes/
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock
  src/hermes/
  tests/
  docs/ai-agent-handoff.md
```

Desktop files (`src-tauri/`, `src/` UI) land in PROD-004 without deleting the CLI until the GUI covers the same flows.

## Status

Skeleton only. No PDF upload in Phase 1 ([SYS-004](../docs/issues.yml)).

## Commands (once the package exists)

```bash
cd hermes
uv sync --frozen --extra dev
uv run pytest
```
