# AI Agent Handoff — delphi-engine

## Identity

| Field | Value |
| --- | --- |
| **System** | Delphi Engine: research-path and patent-whitespace assistant with hindcasting |
| **Type** | Workspace monorepo of isolated component folders (Python 3.13 / uv per package in Phase 1; Tauri/React in PROD-004) |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md`, `docs/prototype-corpus.md`, `docs/prototype-graphs.md` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.2.1/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Planning only. Analog pins and the authored backlog exist. No component `pyproject.toml` yet. Corpus is named ([SYS-009](issues.yml)): transformers/FMs, bounded computer vision, steganography, 2D codes. Dual graphs (citation + content vs other papers) are locked ([SYS-010](issues.yml), `docs/prototype-graphs.md`). Phase 1 implementation may start with contracts; ingest must apply the caps in `docs/prototype-corpus.md`.

| Folder | Path | Notes |
| --- | --- | --- |
| contracts | `contracts/` | Schema including Category, PdfUpload, PathRequest.kind. |
| delphi | `delphi/` | Catalog API. `cites` + `similar_to` + pgvector ([SYS-002](issues.yml), [SYS-010](issues.yml)). |
| daedalus | `daedalus/` | Ingest, PDF metadata/bibliography/body, embeddings vs other papers ([PROTO-008](issues.yml), [PROTO-009](issues.yml)). |
| prometheus | `prometheus/` | `research_path` or `patent_whitespace`. MaskedContext only. SYS-006 provider. |
| epimetheus | `epimetheus/` | Hindcasting. Leak-proof temporal masks. |
| hermes | `hermes/` | Phase 1 CLI with consented PDF upload ([PROTO-006](issues.yml)); Phase 2 Tauri ([PROD-004](issues.yml)). |

Root owns GitHub templates, Cursor rules, `docs/issues.yml`, analog submodules, and `docs/proposal/guardrails/`.

## How to run checks

```bash
bash scripts/check-ci-local.sh
bash scripts/issues-sync.sh --validate-only
git -C docs/guardrails describe --tags --exact-match HEAD
git -C .github/scaffold describe --tags --exact-match HEAD
```

## Analog pins (TOOL-001)

| Companion | How it is pinned |
| --- | --- |
| `pirlruc/guardrails` | Git submodule at `docs/guardrails/` tag **1.3.0** |
| `pirlruc/github-scaffold` | Git submodule at `.github/scaffold/` tag **1.2.0** |
| `pirlruc/methodologies` | Cited by tag `1.2.1`. Not a submodule. |

TS-* gates: [`docs/proposal/guardrails/`](proposal/guardrails/README.md) ([TOOL-002](issues.yml)). Not org defaults.

## Locked decisions (do not reopen silently)

- Six folders including **prometheus** and **contracts** ([SYS-005](issues.yml)).
- Cloud LLM is allowed; Local (OpenAI-compatible, e.g. Ollama/vLLM) and Fake adapters are mandatory ([SYS-006](issues.yml)).
- Users are **scientists and patent searchers**; query kind is `research_path` or `patent_whitespace` ([SYS-007](issues.yml)).
- Prototype requires consented PDF upload, metadata extraction, and dual graphs (citation + content vs other papers) ([SYS-004](issues.yml), [SYS-008](issues.yml), [SYS-010](issues.yml)).
- Hermes desktop is Tauri + React; follow the TS proposal until upstreamed ([TOOL-002](issues.yml), [PROD-004](issues.yml)).
- First corpus subcategories: `transformers_foundation_models`, `computer_vision` (bounded), `steganography`, `two_d_codes` ([SYS-009](issues.yml)).
- GitHub Actions: `workflow_dispatch` only ([GATE-001](issues.yml)).

## Suggested next work

1. PROTO-001 contracts (Extraction metadata, Neighborhood modes, PathRequest.kind).
2. PROTO-002 Delphi neighborhoods, PROTO-003 ingest, PROTO-008 extract, PROTO-009 content graph.
3. Run `quality` on GitHub only when you choose to spend minutes (`bash scripts/check-ci-local.sh` is free).

## Known pitfalls

- Private analog repos 404 unless `CURSOR_REPO_READ_TOKEN` is available. `.gitmodules` must stay tokenless.
- `git remote -v` may display rewritten `x-access-token` URLs from a global `insteadOf`.
- Creating GitHub issues is a publishing action.
- Proposal guardrails under `docs/proposal/guardrails/` must not be read as `docs/guardrails/` thresholds.

*Last updated: 2026-08-19 (SYS-010 dual citation and content graphs)*
