# AI Agent Handoff — delphi-engine

## Identity

| Field | Value |
| --- | --- |
| **System** | Delphi Engine: research-path and patent-whitespace assistant with hindcasting |
| **Type** | Workspace monorepo of isolated component folders (Python 3.13 / uv per package in Phase 1; Tauri/React in PROD-004) |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md`, `docs/prototype-corpus.md` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.2.1/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Planning only. Analog pins and the authored backlog exist. No component `pyproject.toml` yet. **Do not start PROTO-003 until SYS-009 names the corpus field.** Do not start other Phase 1 code until that field is named if the work depends on the slice (ingest, eval). Contracts/Delphi skeletons may be prepared but the owner asked not to advance implementation while SYS-009 is open.

| Folder | Path | Notes |
| --- | --- | --- |
| contracts | `contracts/` | Schema including Category, PdfUpload, PathRequest.kind. |
| delphi | `delphi/` | Catalog API. Postgres + pgvector ([SYS-002](issues.yml)). Generate by kind+category. |
| daedalus | `daedalus/` | OpenAlex + patent slice of the named field; PDF extraction ([PROTO-008](issues.yml)). |
| prometheus | `prometheus/` | `research_path` or `patent_whitespace`. MaskedContext only. SYS-006 provider. |
| epimetheus | `epimetheus/` | Hindcasting. Leak-proof temporal masks. |
| hermes | `hermes/` | Phase 1 CLI with consented PDF upload ([PROTO-006](issues.yml)); Phase 2 Tauri ([PROD-004](issues.yml)). |

Root owns GitHub templates, Cursor rules, `docs/issues.yml`, analog submodules, and `docs/proposal/guardrails/`.

## How to run checks

```bash
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
- Prototype requires consented PDF upload, extraction, and category/subcategory generate ([SYS-004](issues.yml), [SYS-008](issues.yml)).
- Hermes desktop is Tauri + React; follow the TS proposal until upstreamed ([TOOL-002](issues.yml), [PROD-004](issues.yml)).

## Open decision (blocks ingest)

- First corpus field is **unnamed**. Explanation and candidates: [`docs/prototype-corpus.md`](prototype-corpus.md). Record the choice on [SYS-009](issues.yml).

## Suggested next work

1. Owner names the field on SYS-009 (OpenAlex filter + CPC prefixes).
2. Then PROTO-001 contracts (Category, PdfUpload, PathRequest.kind).
3. Do not start SCALE-* until PROTO-007 has the PDF demo **and** hindcast numbers.

## Known pitfalls

- Private analog repos 404 unless `CURSOR_REPO_READ_TOKEN` is available. `.gitmodules` must stay tokenless.
- `git remote -v` may display rewritten `x-access-token` URLs from a global `insteadOf`.
- Creating GitHub issues is a publishing action.
- Proposal guardrails under `docs/proposal/guardrails/` must not be read as `docs/guardrails/` thresholds.

*Last updated: 2026-08-19 (clarifications: PDF prototype, dual audience, LLM adapters, TS proposal)*
