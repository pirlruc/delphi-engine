# AI Agent Handoff — hermes

Client only. Identifier batch-check never requires file bytes. PDF upload requires consent that names Delphi as destination.

**Last updated:** 2026-08-19

## Current slice

Walking skeleton ([PROTO-006](../../docs/issues.yml)). Typer CLI talks to Delphi over HTTP and caches last JSON in SQLite.

## Constraints

- Phase 1 is a Python CLI so PY-* gates apply: upload PDF, show extracted metadata, show citation vs content neighborhoods, batch-check IDs, query by category/subcategory.
- Upload without `--consent-destination delphi` must fail tests (exit 2).
- Generate kinds: `research_path` and `patent_whitespace`, filtered by category/subcategory.
- Content neighborhood is similar **other papers**, not a graph of the uploaded PDF alone ([SYS-010](../../docs/issues.yml)).
- Zotero/Tauri is [PROD-004](../../docs/issues.yml); follow `docs/proposal/guardrails/typescript/`.

## Suggested next work

Exercise both generate kinds against a real consented PDF once Delphi is serving ([PROTO-007](../../docs/issues.yml)).
