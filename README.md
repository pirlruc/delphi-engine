# delphi-engine

Workspace for a system that proposes **research paths** and **patent whitespaces** from the literature you already have — global catalogs plus a local library — and tests those proposals by **hindcasting**.

Given only papers and patents published before time *T*, can an AI propose the next plausible innovation in that space? If the proposal resembles what actually happened (or a useful gap that did not), the system is doing its job. If it cannot, a larger graph will not save it.

This repository currently holds every component as an **isolated folder**. GitHub Issues, CI, and analog pins live at the workspace root. Each folder is shaped like a standalone pirlruc package so it can become its own git repository later ([SCALE-003](docs/issues.yml)).

## Methodology

[GitHub Issue-native ADR](https://github.com/pirlruc/methodologies/tree/1.2.1/github-issue-adr) — Epic = decision record, optional Y-statement, no ADR markdown files. Templates: [pirlruc/github-scaffold](https://github.com/pirlruc/github-scaffold) @ **1.2.0**. Quality: pin [pirlruc/guardrails](https://github.com/pirlruc/guardrails) at `docs/guardrails/` @ **1.3.0**. Applies to **new issues only**.

Authored backlog: [`docs/issues.yml`](docs/issues.yml).

```bash
bash scripts/setup-issue-scaffold.sh
bash scripts/issues-sync.sh --repo pirlruc/delphi-engine --yaml docs/issues.yml --validate-only
bash scripts/issues-sync.sh --repo pirlruc/delphi-engine --yaml docs/issues.yml --dry-run
```

Creating labels, milestones, and issues needs a GitHub token with **Issues: Read and write**. Publishing issues is gated — dry-run first.

## Components

| Folder | Role in the product |
| --- | --- |
| [`contracts/`](contracts/) | Shared Pydantic models and OpenAPI. The only package other folders may depend on. |
| [`delphi/`](delphi/) | Catalog and query API. Batch identifier checks, dated neighborhoods. Not the ingest or eval orchestrator. |
| [`daedalus/`](daedalus/) | Ingest. Prototype: public metadata (OpenAlex). Product: patents, optional LLM extraction, queues. |
| [`prometheus/`](prometheus/) | Generates research paths and whitespace hypotheses from a **masked** past-only neighborhood. |
| [`epimetheus/`](epimetheus/) | Hindcasting eval harness. Temporal masks must not leak the future. |
| [`hermes/`](hermes/) | User client. Prototype: Python CLI + local SQLite. Product: desktop + Zotero + PDF consent. |

```mermaid
flowchart LR
  Hermes["hermes"] -->|batch-check / path query| Delphi["delphi"]
  Daedalus["daedalus"] -->|upsert works and edges| Delphi
  Delphi -->|past-only neighborhood| Prometheus["prometheus"]
  Epimetheus["epimetheus"] -->|mask + score| Delphi
  Epimetheus --> Prometheus
  Hermes --> Prometheus
```

## Plan in one page

**Phase 0** — decisions already authored as Epics (`SYS-001` … `SYS-005`): folder isolation, Postgres+pgvector for the prototype, exact identity matching, no PDF upload, six components.

**Phase 1 — prototype** — one public paper field, REST API, citation graph, Prometheus generator, leak-proof hindcasting, Hermes CLI. Done when `PROTO-007` has numbers.

**Phase 2 — product slice** — patents, embeddings, Zotero desktop, consent for PDFs, fuzzy matching, HITL review queue.

**Phase 3 — scale-out** — split graph/vector engines when measured, streaming ingest, extract folders into standalone repos.

Billion-scale stores (Neptune, clustered Milvus, and similar) are Phase 3, not the first implementation.

## Analog pins

| Companion | How it is pinned |
| --- | --- |
| `pirlruc/guardrails` | Git submodule SHA at `docs/guardrails/` (tag **1.3.0**) |
| `pirlruc/github-scaffold` | Git submodule SHA at `.github/scaffold/` (tag **1.2.0**) |
| `pirlruc/methodologies` | Cited by tag (`tree/1.2.1/github-issue-adr`). Not a submodule. |

Private clones need `CURSOR_REPO_READ_TOKEN` (or equivalent) at VM start. `.gitmodules` uses HTTPS URLs without tokens.

## Documentation

- [`docs/ai-agent-handoff.md`](docs/ai-agent-handoff.md)
- [`docs/issues.yml`](docs/issues.yml)
- [`docs/limitations.md`](docs/limitations.md)
