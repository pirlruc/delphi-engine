# hermes

Local research hub (client).

Treat this folder as if it were a standalone repository (`pirlruc/hermes`). Depend on `contracts`. Talk to Delphi over HTTP. Never import server internals.

## Role

Let a scientist or patent searcher overlay a document they have on the global catalog, then inspect AI-generated **research paths** and **patent whitespaces** by category/subcategory.

**Phase 1 ([PROTO-006](../docs/issues.yml)):** Python CLI + local SQLite cache.

- Batch-check identifiers without uploading a file.
- Prompt for **consent** (destination named), then upload one PDF.
- Show extracted categories/subcategories; allow override.
- Query `research_path` or `patent_whitespace` for those categories.

**Phase 2 ([PROD-004](../docs/issues.yml)):** Tauri + React desktop. First reference manager is local Zotero SQLite. Reuse the same consent rule. Quality follows [`docs/proposal/guardrails/typescript/`](../docs/proposal/guardrails/typescript/) until that pack is upstreamed. Qiqqa and Mendeley wait until Zotero works.

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

Skeleton only. Consented PDF upload is in Phase 1 ([SYS-004](../docs/issues.yml)).

## Commands (once the package exists)

```bash
cd hermes
uv sync --frozen --extra dev
uv run pytest
```
