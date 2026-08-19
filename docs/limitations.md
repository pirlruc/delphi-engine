# Limitations

Known limits that are not GitHub issues. Product gaps that we intend to close live in [`docs/issues.yml`](issues.yml).

## CI

- Workflows are `workflow_dispatch` only ([GATE-001](issues.yml)). They do not run on push, pull request, or schedule.
- Local parity: `bash scripts/check-ci-local.sh`.

## Not yet software

- No running API, ingest, generator, eval harness, or client.
- No GitHub labels/milestones until `scripts/setup-issue-scaffold.sh` is run with Issues write permission.
- `docs/issues.yml` is authored locally; GitHub Issues are not published until a gated live sync.

## Prototype (once software exists)

- Four subcategories: transformers/FMs (capped), bounded computer vision, steganography, 2D codes. Not a global corpus. See [`docs/prototype-corpus.md`](prototype-corpus.md).
- Consented single-PDF upload (not bulk Zotero sync).
- LLM adapters: Fake in tests; cloud or local in live runs ([SYS-006](issues.yml)).
- No GraphQL, no distributed graph or vector databases.
- Hermes Phase 1 is a CLI; Tauri is [PROD-004](issues.yml).

## Guardrails

- Pinned language pack is Python 3.13 at `docs/guardrails/` @ 1.3.0.
- TypeScript/Tauri gates live in [`docs/proposal/guardrails/`](proposal/guardrails/README.md) until TOOL-002 is upstreamed. Do not copy them into `docs/guardrails/` (that path is a submodule).
- Org Python floors are 95% statement and branch coverage once packages exist.

## Environment

- `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI will need `GUARDRAILS_READ_TOKEN` (or equivalent) to checkout the `docs/guardrails` gitlink.
