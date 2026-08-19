# Limitations

Known limits that are not GitHub issues. Product gaps that we intend to close live in [`docs/issues.yml`](issues.yml).

## CI

- Workflows are `workflow_dispatch` only ([GATE-001](issues.yml)). They do not run on push, pull request, or schedule.
- Local parity: `bash scripts/check-ci-local.sh` (YAML + `scripts/python-gates.sh` unless `SKIP_PYTHON_GATES=1`).

## Walking skeleton (not product scale)

- Default serve path is an **in-memory catalog** plus the Fake LLM. Postgres 16 + pgvector is in `docker-compose.yml` and is not wired into `scripts/serve_prototype.py` yet ([SYS-002](issues.yml), [PROTO-002](issues.yml)).
- Catalog ingest for the demo is the eight-work fixture in `daedalus/src/daedalus/fixtures/slice.json`. OpenAlex/PatentsView **HTTP** page fetch is not live ([PROTO-003](issues.yml)).
- Embeddings are deterministic hash bag-of-words, not a hosted embedding model.
- No GitHub labels/milestones until `scripts/setup-issue-scaffold.sh` is run with Issues write permission.
- `docs/issues.yml` is authored locally; GitHub Issues are not published until a gated live sync.

## Prototype corpus and graphs

- Four subcategories: transformers/FMs (capped), bounded computer vision, steganography, 2D codes. Not a global corpus. See [`docs/prototype-corpus.md`](prototype-corpus.md).
- Consented single-PDF upload (not bulk Zotero sync).
- Dual graphs: directed `cites` plus top-k `similar_to`. See [`docs/prototype-graphs.md`](prototype-graphs.md).
- Catalog works in the content graph use **title + abstract**, not licensed full text, unless the user uploaded that paper. Richer re-embed is [PROD-003](issues.yml).
- Content-graph edges are nearest-neighbor similarities, not a full pairwise matrix of the slice.
- Patent coverage in the fixture is one CPC-tagged record plus OpenAlex-shaped papers, not the full CPC tree. CPC is a category scheme ([SYS-008](issues.yml)), not exhaustive patent ingest.
- LLM adapters: Fake in tests and in the default serve path; cloud or local in live runs ([SYS-006](issues.yml)).
- No GraphQL, no distributed graph or vector databases.
- Hermes Phase 1 is a CLI; Tauri is [PROD-004](issues.yml).
- PROTO-007 go/no-go still needs a recorded PDF demo plus mean hindcast scores on the ingested slice, not only the tiny CLI fixture.

## Guardrails

- Pinned language pack is Python 3.13 at `docs/guardrails/` @ 1.3.0.
- TypeScript/Tauri gates live in [`docs/proposal/guardrails/`](proposal/guardrails/README.md) until TOOL-002 is upstreamed. Do not copy them into `docs/guardrails/` (that path is a submodule).
- Org Python floors are 95% statement and branch coverage.
- This prototype PR exceeds the PY-DELIV-001 soft limit of 500 lines because it lands six packages at once.

## Environment

- `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI will need `GUARDRAILS_READ_TOKEN` (or equivalent) to checkout the `docs/guardrails` gitlink.
- Packages require uv with CPython 3.13 even when the VM's `/usr/bin/python3` is 3.12.
