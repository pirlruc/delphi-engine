# Limitations

Known limits that are not GitHub issues. Product gaps that we intend to close live in [`docs/issues.yml`](issues.yml).

## Not yet software

- No running API, ingest, generator, eval harness, or client. Phase 1 starts at PROTO-001.
- No GitHub labels/milestones until `scripts/setup-issue-scaffold.sh` is run with Issues write permission.
- `docs/issues.yml` is authored locally; GitHub Issues are not published until a gated live sync.

## Prototype defaults (overridable by Epic)

- One public paper field via OpenAlex, not a global corpus.
- No patents, no user PDFs, no Zotero, no GraphQL, no distributed graph or vector databases.
- LLM-as-judge and path generation use a fake provider in tests; live model choice is not locked.

## Guardrails

- Language pack is Python. Hermes desktop (Tauri/React) in PROD-004 has no TypeScript pack in pirlruc/guardrails; that Epic must record how quality is enforced or extract Hermes to a repo that can pin a future pack.
- Org Python floors are 95% statement and branch coverage once packages exist. Empty folders have no runtime to measure.

## Environment

- `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI will need `GUARDRAILS_READ_TOKEN` (or equivalent) to checkout the `docs/guardrails` gitlink, same pattern as github-scaffold consumers.
