# hermes

Local research hub (client).

Treat this folder as if it were a standalone repository (`pirlruc/hermes`). Depend on `contracts`. Talk to Delphi over HTTP. Never import server internals.

## Role

Let a scientist or patent searcher overlay a document they have on the global catalog, then inspect AI-generated **research paths** and **patent whitespaces** by category/subcategory.

**Phase 1 ([PROTO-006](../docs/issues.yml)):** Python CLI + local SQLite cache.

- Batch-check identifiers without uploading a file.
- Require **consent** (`--consent-destination delphi`), then upload one PDF.
- Print extracted **title, authors, keywords**, bibliography matches, suggested subcategory.
- Show **citation** and **content** neighborhoods (content = similar other papers, not the PDF in isolation).
- Query `research_path` or `patent_whitespace` for those categories.

**Phase 2 ([PROD-004](../docs/issues.yml)):** the Tauri + React app lives in [pirlruc/hermes-desktop](https://github.com/pirlruc/hermes-desktop). This folder stays the Python client the tests use. Quality for the desktop app follows the org [node pack](https://github.com/pirlruc/guardrails/tree/1.15.0/node). Qiqqa and Mendeley wait until Zotero works.

## Layout (Phase 1)

```
hermes/
  README.md
  CHANGELOG.md
  pyproject.toml
  src/hermes/
  tests/
  docs/ai-agent-handoff.md
```

Desktop files (`src-tauri/`, `src/` UI) land in PROD-004 without deleting the CLI until the GUI covers the same flows.

## Status

Walking skeleton. Consented PDF upload is in Phase 1 ([SYS-004](../docs/issues.yml)). Upload without `--consent-destination delphi` exits 2.

## Commands

Start Delphi first (`bash scripts/serve-prototype.sh` from the workspace root). Fixture seed work id: `11111111-1111-1111-1111-111111111111`.

```bash
cd hermes
uv sync --frozen --extra dev
uv run pytest
uv run hermes batch-check --doi 10.1000/qr-2014
uv run hermes upload paper.pdf --subcategory two_d_codes --consent-destination delphi
uv run hermes neighborhood 11111111-1111-1111-1111-111111111111 --subcategory two_d_codes --mode union
uv run hermes generate research_path --subcategory two_d_codes --seed-work-id 11111111-1111-1111-1111-111111111111
uv run hermes generate research_path --subcategory two_d_codes --extraction-id 22222222-2222-2222-2222-222222222222 --as-of 2016-01-01
uv run hermes reprint upload
```
