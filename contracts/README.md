# contracts

Shared schema for Delphi Engine.

Treat this folder as if it were a standalone repository (`pirlruc/delphi-contracts`). Other folders may depend on this package. This package must not import `delphi`, `daedalus`, `prometheus`, `epimetheus`, or `hermes`.

## Role

Owns Pydantic models and the generated OpenAPI document for Work identity, Category (`scheme`: `openalex_topic` or `cpc`, plus subcategory parent links), batch existence checks, consented PdfUpload, Extraction (title, authors, keywords, bibliography, body text), Neighborhood (`citation`, `content`, `union`), PathRequest (`kind`: `research_path` or `patent_whitespace`), and eval runs. Delphi implements the HTTP API; everyone else speaks this contract.

## Layout

```
contracts/
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock
  src/delphi_contracts/
  tests/
  docs/ai-agent-handoff.md
```

Matches [pymjolnir](https://github.com/pirlruc/pymjolnir): `src/` layout, uv, Google docstrings, pytest. Import name is `delphi_contracts`.

## Status

Walking skeleton ([PROTO-001](../docs/issues.yml)). OpenAPI is generated from the models and checked in at `src/delphi_contracts/openapi.json`.

## Commands

```bash
cd contracts
uv sync --frozen --extra dev
uv run pytest
uv run ruff check src tests
```
