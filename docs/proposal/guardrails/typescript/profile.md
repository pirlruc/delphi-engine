# TypeScript Org Profile (Proposal)

Numeric gates: [`profile.thresholds.yml`](profile.thresholds.yml). Principles: [`guardrails.md`](guardrails.md).

## Fixed baseline

| Area | Value | Guardrail |
|------|-------|-----------|
| Node.js | 22 LTS | TS-RUN-001, TS-RUN-003 |
| Next LTS | Node 24 expected Active LTS 2026-10; re-evaluate by 2027-04 | TS-RUN-003 |
| Package manager | `pnpm` with a committed `pnpm-lock.yaml` | TS-RUN-001 |
| Language | TypeScript 5.x, `strict` + `noUncheckedIndexedAccess` | TS-QUAL-002 |

## Predetermined tools (recommended)

| Category | Org default | Guardrail |
|----------|-------------|-----------|
| Formatter / linter | `biome` (format + lint) | TS-RUN-002, TS-QUAL-001 |
| Type checking | `tsc --noEmit` | TS-RUN-002, TS-QUAL-002 |
| Unit tests | `vitest` | TS-TEST-001 |
| Coverage | `@vitest/coverage-v8` | TS-TEST-002 |
| Complexity | biome/eslint `complexity` via CI script reading the YAML floors | TS-CPLX-001 |
| Doc coverage | `typedoc` coverage gate | TS-DOC-001 |
| Secret scan | `gitleaks` | TS-SEC-003 |
| Security SAST | `semgrep`, `osv-scanner` | TS-SEC-002 |
| Statement coverage | >= `statement_coverage`% per package | TS-TEST-002 |
| Branch coverage | >= `branch_coverage`% per package | TS-TEST-002 |
| Doc coverage | >= `doc_coverage`% of exported symbols | TS-DOC-001 |
| Cyclomatic complexity | max <= `max_cyclomatic_complexity` | TS-CPLX-001 |
| Function lines | max <= `max_function_lines` | TS-CPLX-002 |
| PR size | soft limit `pr_size_soft_limit_lines` lines | TS-DELIV-001 |
| Tauri / Rust | `rustfmt`, `clippy -D warnings` | TS-DESK-001, TS-DESK-002 |

This pack does **not** invent a maintainability-index average. Org Python uses radon MI;
TypeScript tooling used here does not produce that number. TS-CPLX-002 uses function
length instead. If guardrails later adds a TS MI tool, replace the key rather than
silently mapping it to radon.

## Deviation rule

See [pirlruc/guardrails](https://github.com/pirlruc/guardrails#deviation-rule). Lowering
coverage or complexity gates requires an Epic. Cite the Guardrail ID (e.g. `TS-TEST-002`).
