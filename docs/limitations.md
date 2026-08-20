# Limitations

Known limits that are not GitHub issues. Product gaps that we intend to close live in [`docs/issues.yml`](issues.yml).

## CI

- Workflows are `workflow_dispatch` only ([GATE-001](issues.yml)). They do not run on push, pull request, or schedule.
- Local parity: `bash scripts/check-ci-local.sh` (YAML + `scripts/python-gates.sh` unless `SKIP_PYTHON_GATES=1`).

## Walking skeleton (not product scale)

- Default serve path is an **in-memory catalog** plus the Fake LLM. Postgres 16 is wired behind `Catalog` (`PostgresCatalog`) when `DELPHI_DATABASE_URL` is set (`scripts/serve_prototype.py --database-url`, Compose `delphi` service). k-NN for `similar_to` still uses in-process cosine on stored `double precision[]` vectors; the Compose image is pgvector so SCALE-001 can switch operators later.
- Catalog ingest for the demo is the eight-work fixture. OpenAlex **live** paging exists (`daedalus --live --per-subcategory N`); default remains the fixture. Tens-of-thousands ingest is not the default ([PROTO-003](issues.yml)). PatentsView live fetch needs `PATENTSVIEW_API_KEY`. EPO/WIPO/PatSnap/Lens.org clients exist (`daedalus --live-patents`); they skip sources without credentials. Official PATENTSCOPE search is a paid SOAP service — the WIPO client talks to a REST JSON gateway (`WIPO_PATENTSCOPE_URL`).
- Embeddings use the SYS-006 provider (Fake hash by default; cloud or local when `DELPHI_LLM_KIND` is set).
- No GitHub labels/milestones until `scripts/setup-issue-scaffold.sh` is run with Issues write permission.
- `docs/issues.yml` is authored locally; GitHub Issues are not published until a gated live sync.

## Prototype corpus and graphs

- Four subcategories: transformers/FMs (capped), bounded computer vision, steganography, 2D codes. Not a global corpus. See [`docs/prototype-corpus.md`](prototype-corpus.md).
- Consented single-PDF upload (not bulk Zotero sync).
- Dual graphs: directed `cites` plus top-k `similar_to`. See [`docs/prototype-graphs.md`](prototype-graphs.md).
- Catalog works in the content graph use composed title/abstract/CPC/claims (and truncated upload body), not licensed full text. See [`docs/evolution.md`](evolution.md). Domain/JEPA encoders remain [PROD-003](issues.yml).
- Content-graph edges are nearest-neighbor similarities, not a full pairwise matrix of the slice.
- Patent coverage in the fixture is one CPC-tagged record plus OpenAlex-shaped papers, not the full CPC tree. CPC is a category scheme ([SYS-008](issues.yml)), not exhaustive patent ingest.
- LLM adapters: Fake in tests and in the default serve path; cloud or local in live runs ([SYS-006](issues.yml)).
- No GraphQL, no distributed graph or vector databases.
- Hermes Phase 1 is a CLI; Tauri is [PROD-004](issues.yml).
- Judge rubric: [`docs/eval-rubric.md`](eval-rubric.md). Demo artifact: [`docs/prototype-demo.json`](prototype-demo.json).

## Guardrails

- Pinned language pack is Python 3.13 at `docs/guardrails/` @ 1.3.0.
- TypeScript/Tauri gates live in [`docs/proposal/guardrails/`](proposal/guardrails/README.md) until TOOL-002 is upstreamed. Do not copy them into `docs/guardrails/` (that path is a submodule).
- Org Python floors are 95% statement and branch coverage.

## Environment

- `pirlruc/guardrails` and `pirlruc/github-scaffold` are private. CI will need `GUARDRAILS_READ_TOKEN` (or equivalent) to checkout the `docs/guardrails` gitlink.
- Packages require uv with CPython 3.13 even when the VM's `/usr/bin/python3` is 3.12.
