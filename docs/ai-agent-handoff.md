# AI Agent Handoff — delphi-engine

## Identity

| Field | Value |
| --- | --- |
| **System** | Delphi Engine: research-path and patent-whitespace assistant with hindcasting |
| **Type** | Workspace monorepo of isolated component folders (Python 3.13 / uv per package in Phase 1) |
| **Docs** | `docs/ai-agent-handoff.md`, `docs/issues.yml`, `docs/limitations.md` |
| **Methodology** | [github-issue-adr](https://github.com/pirlruc/methodologies/tree/1.2.1/github-issue-adr) (Epic = decision record, no ADR markdown files) |

## Current slice

Planning only. Analog pins and the authored backlog exist. No component `pyproject.toml` yet — that starts at [PROTO-001](issues.yml).

| Folder | Path | Notes |
| --- | --- | --- |
| contracts | `contracts/` | Shared schema. Other packages depend on this, not on siblings. |
| delphi | `delphi/` | Catalog API. Prototype store is Postgres + pgvector ([SYS-002](issues.yml)). |
| daedalus | `daedalus/` | Ingest. Prototype is OpenAlex metadata, no PDFs ([SYS-004](issues.yml)). |
| prometheus | `prometheus/` | Path generator. Must accept a pre-masked context; must not query the catalog itself. |
| epimetheus | `epimetheus/` | Hindcasting. Leak-proof temporal masks are the sacred constraint. |
| hermes | `hermes/` | Phase 1 CLI; Phase 2 Tauri + Zotero ([PROTO-006](issues.yml), [PROD-004](issues.yml)). |

Root owns GitHub templates, Cursor rules, `docs/issues.yml`, and analog submodules. Component folders must remain extractable ([SYS-001](issues.yml), [SCALE-003](issues.yml)).

## How to run checks

```bash
bash scripts/issues-sync.sh --validate-only
git -C docs/guardrails describe --tags --exact-match HEAD
git -C .github/scaffold describe --tags --exact-match HEAD
```

Issue publish:

```bash
bash scripts/setup-issue-scaffold.sh
bash scripts/issues-sync.sh --repo pirlruc/delphi-engine --yaml docs/issues.yml --dry-run
```

Do not live-sync issues without approval. `gh` in this environment may be issues=read only.

## Analog pins (TOOL-001)

| Companion | How it is pinned |
| --- | --- |
| `pirlruc/guardrails` | Git submodule at `docs/guardrails/` tag **1.3.0** |
| `pirlruc/github-scaffold` | Git submodule at `.github/scaffold/` tag **1.2.0** |
| `pirlruc/methodologies` | Cited by tag `1.2.1`. Not a submodule. |

## github-issue-adr

Authored backlog: [`docs/issues.yml`](issues.yml). Targets: [`docs/issues-sync-targets.yml`](issues-sync-targets.yml). Deviations: [`docs/guardrail-deviations.yml`](guardrail-deviations.yml) (none). Do not invent `approved_by`. Do not create `docs/adr/`.

## Assumptions encoded in Phase 0

These are decision-record defaults. Change them with an Epic update, not a silent README edit.

- Prototype corpus: one OpenAlex computer-science / ML slice (override if the owner names another field).
- Prototype modality: papers only. Patents are [PROD-001](issues.yml).
- LLM: provider interface with a deterministic fake in tests. Cloud keys are optional for local eval.
- Hermes Phase 1: Python CLI, not Tauri.
- Exact identifier matching only until [PROD-005](issues.yml).
- No raw PDF bytes in Phase 1 APIs.

## Suggested next work

1. Close [TOOL-001](issues.yml) after labels/milestones exist on GitHub (owner token).
2. Implement [PROTO-001](issues.yml) (contracts) then [PROTO-002](issues.yml) (Delphi API).
3. Do not start SCALE-* or desktop Hermes until [PROTO-007](issues.yml) has hindcasting numbers.

## Known pitfalls

- Private analog repos 404 unless `CURSOR_REPO_READ_TOKEN` (contents:read on guardrails and github-scaffold) is available. `.gitmodules` must stay tokenless.
- `git remote -v` may display rewritten `x-access-token` URLs from a global `insteadOf`; stored submodule URLs are HTTPS without tokens.
- Creating GitHub issues is a publishing action. `--validate-only` does not need a write token; live sync does.
- Python 3.13, uv, Google docstrings, and 95/95 coverage floors apply once a package exists ([`docs/guardrails/python/profile.md`](https://github.com/pirlruc/guardrails/blob/1.3.0/python/profile.md)).

*Last updated: 2026-08-19 (prototype-to-product plan authored)*
