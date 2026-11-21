# AI Agent Handoff — delphi-engine

## Identity

| Field | Value |
| --- | --- |
| **System** | Delphi Engine: research-path and patent-whitespace assistant with hindcasting |
| **Type** | Workspace monorepo of isolated component folders (Python 3.13 / uv per package in Phase 1; Tauri/React in PROD-004) |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md`, `docs/prototype-corpus.md`, `docs/prototype-graphs.md`, `docs/evolution.md` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.11.1/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Walking-skeleton prototype. Six Python packages, in-memory catalog by default, optional `PostgresCatalog` via `DELPHI_DATABASE_URL`, Fake LLM (override with `DELPHI_LLM_*`), fixture SYS-009 slice, dual graphs (`cites` + `similar_to`), consented PDF upload, Hermes CLI, Epimetheus slice hindcast. `bash scripts/demo-prototype.sh` writes `docs/prototype-demo.json`. Compose brings up API plus Postgres (`bash scripts/compose-up.sh`). Live OpenAlex paging: `daedalus --live`. Multi-office patents: `daedalus --live-patents` (EPO, WIPO JSON gateway, PatSnap, Lens.org).

| Folder | Path | Notes |
| --- | --- | --- |
| contracts | `contracts/` | `delphi_contracts` models + OpenAPI. |
| delphi | `delphi/` | FastAPI. `MemoryCatalog`. Ports for extractor/embedder/generator. |
| daedalus | `daedalus/` | Fixture ingest, PDF extract, composed embeddings vs other papers. |
| prometheus | `prometheus/` | Import `delphi_prometheus`. MaskedContext only. |
| epimetheus | `epimetheus/` | Dual-graph temporal masks + Fake judge artifact. |
| hermes | `hermes/` | CLI: batch-check, consented upload, neighborhood, generate. |

Root owns GitHub templates, Cursor rules, `docs/issues.yml`, analog submodules, the uv workspace, and `scripts/serve_prototype.py`. Sibling imports except contracts are forbidden in package **src**. Tests and `scripts/serve_prototype.py` may wire siblings.

## How to run

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/serve-prototype.sh
# Postgres (when DELPHI_DATABASE_URL is set, e.g. docker compose up --build):
# bash scripts/serve-prototype.sh --database-url "$DELPHI_DATABASE_URL"
# Live OpenAlex / patent pages (small cap; pass JSON to serve --records):
# cd daedalus && uv run daedalus --live --per-subcategory 5 --output /tmp/slice.json
# cd daedalus && uv run daedalus --live-patents --per-subcategory 5 --output /tmp/patents.json
# other terminal:
cd hermes && uv run hermes batch-check --doi 10.1000/qr-2014
cd hermes && uv run hermes upload paper.pdf --subcategory two_d_codes --consent-destination delphi
cd epimetheus && uv run epimetheus --output evalrun.json
```

## How to run checks

```bash
bash scripts/check-ci-local.sh
bash scripts/python-gates.sh
bash scripts/issues-sync.sh --validate-only
git -C docs/guardrails describe --tags --exact-match HEAD
git -C .github/scaffold describe --tags --exact-match HEAD
```

System Python may be 3.12. Packages require **uv + CPython 3.13**.

## Analog pins (TOOL-001)

| Companion | How it is pinned |
| --- | --- |
| `pirlruc/guardrails` | Git submodule at `docs/guardrails/` tag **1.15.0** |
| `pirlruc/github-scaffold` | Git submodule at `.github/scaffold/` tag **1.12.0** |
| `pirlruc/methodologies` | Cited by tag `1.11.1`. Not a submodule. |

JavaScript and TypeScript gates are the org `node/` pack ([TOOL-002](issues.yml)).

## Locked decisions (do not reopen silently)

- Six folders including **prometheus** and **contracts** ([SYS-005](issues.yml)).
- Cloud LLM is allowed; Local (OpenAI-compatible, e.g. Ollama/vLLM) and Fake adapters are mandatory ([SYS-006](issues.yml)).
- Users are **scientists and patent searchers**; query kind is `research_path` or `patent_whitespace` ([SYS-007](issues.yml)).
- Prototype requires consented PDF upload, metadata extraction, and dual graphs (citation + content vs other papers) ([SYS-004](issues.yml), [SYS-008](issues.yml), [SYS-010](issues.yml)).
- Hermes desktop is Tauri + React in pirlruc/hermes-desktop; follow the org node pack ([TOOL-002](issues.yml), [PROD-004](issues.yml)).
- First corpus subcategories: `transformers_foundation_models`, `computer_vision` (bounded), `steganography`, `two_d_codes` ([SYS-009](issues.yml)).
- GitHub Actions: `workflow_dispatch` only ([GATE-001](issues.yml)).

## Suggested next work

1. Run Compose on a Docker host: `bash scripts/compose-up.sh` and confirm `/health` plus Hermes against Postgres ([PROTO-002](issues.yml), [SYS-002](issues.yml)).
2. Raise `--per-subcategory` / `--live-patents` toward SYS-009 caps once keys are configured ([PROTO-003](issues.yml), [PROD-001](issues.yml)).
3. Non-Fake LLM for a live hindcast once a provider is configured (`DELPHI_LLM_KIND=cloud|local`, [SYS-006](issues.yml)).

## Known pitfalls

- Private analog repos 404 unless `CURSOR_REPO_READ_TOKEN` is available. `.gitmodules` must stay tokenless.
- `git remote -v` may display rewritten `x-access-token` URLs from a global `insteadOf`.
- Creating GitHub issues is a publishing action.
- Proposal guardrails under `docs/proposal/guardrails/` must not be read as `docs/guardrails/` thresholds.
- Members share one workspace lockfile at the repository root. Run `uv sync --all-packages --all-extras` from the root.
- Do not use `from __future__ import annotations` in `delphi/app.py`: FastAPI then treats `Depends` as a query field.
- Proposal guardrails were removed. Do not recreate `docs/proposal/`.

- An undated seed (`1970-01-01`) refuses generate unless the request sets `as_of`. `mask_on` is the first forbidden date.
- Root `mypy .` needs the workspace `[tool.mypy]` in `pyproject.toml`, including `python_executable = ".venv/bin/python"`. The quality job runs its own mypy, and that setting is how it sees the workspace install. Do not set `plugins = ["pydantic.mypy"]`. Do not put `.venv` on `mypy_path`; mypy then treats installed modules as user code.
- Postgres needs `cap_add` after `cap_drop: ALL`. KICS query `ce76b7d0` treats any `cap_add` as unrestricted, including the sample that also drops all capabilities, so `.github/kics.config` excludes it.
- `.trivyignore.yaml` entries have no `paths`. Trivy reports these Debian findings against the image name, so a dpkg path never matches. `.grype.yaml` lists the same ids. Both expire 2026-12-20. The image removes pip, setuptools, and ensurepip after installing uv so those Python findings are not ignored.

*Last updated: 2026-11-20 (quality mypy uses the workspace interpreter; Trivy ignores are id-scoped).*
