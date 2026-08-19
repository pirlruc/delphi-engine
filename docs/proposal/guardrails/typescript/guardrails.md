# TypeScript Guardrails (Proposal)

Repository-agnostic principles for TypeScript projects (including React and Tauri
frontends). Org defaults once accepted: [`profile.md`](profile.md).

**Status:** proposal in delphi-engine. Not an org default until copied into
[pirlruc/guardrails](https://github.com/pirlruc/guardrails) and tagged.

## Runtime & Tooling

- **[TS-RUN-001]** Define supported Node.js major, package manager, and lockfile baseline.
- **[TS-RUN-002]** Enforce formatter, linter, and type-checker in CI with local parity.
- **[TS-RUN-003]** Target the current Node.js LTS major. Pin the concrete version and the
  re-evaluation date in `profile.md` (same rule as PY-RUN-003: when the next LTS is
  current, re-evaluate within six months).

## Code Quality

- **[TS-QUAL-001]** Block on agreed lint/type severity; exceptions require owner, rationale, and expiry.
- **[TS-QUAL-002]** `strict` TypeScript (`strict`, `noUncheckedIndexedAccess`) for application and library code.

## Complexity & Maintainability

- **[TS-CPLX-001]** Enforce cyclomatic complexity gates on production TypeScript (see `profile.thresholds.yml`).
- **[TS-CPLX-002]** Enforce file-length and function-length soft gates so complexity stays measurable.

## Testing & Coverage

- **[TS-TEST-001]** Require automated tests for new features and bug fixes.
- **[TS-TEST-002]** Enforce per-package statement and branch coverage thresholds (see `profile.thresholds.yml`).
- **[TS-TEST-003]** Define flaky-test and quarantine policy. UI tests that need the network are not unit tests.

## API & Architecture

- **[TS-API-001]** Public package API changes require migration notes.
- **[TS-API-002]** Cross-package boundary changes require explicit rationale.
- **[TS-API-003]** HTTP clients are generated from the OpenAPI document in `contracts/`; do not hand-copy DTO shapes.

## Performance & Reliability

- **[TS-PERF-001]** Performance-impacting changes require profiling or benchmark evidence.
- **[TS-PERF-002]** Async work must document cancellation and error surfaces (no floating promises).

## Security & Supply Chain

Shared SBOM, provenance, signing, and license gates: in the pinned guardrails tree,
[`supply-chain/guardrails.md`](https://github.com/pirlruc/guardrails/blob/1.3.0/supply-chain/guardrails.md)
(`SC-SBOM-*`, `SC-PROV-*`, `SC-SIGN-*`, `SC-LIC-*`).

- **[TS-SEC-001]** New dependencies require owner and security/license review (license deny gate: SC-LIC-001).
- **[TS-SEC-002]** Enforce vulnerability and SAST scanning in CI.
- **[TS-SEC-003]** Secret scanning in CI and pre-commit.
- **[TS-SEC-004]** Renderer/main-process (Tauri) and browser contexts must not log PDF bytes, consent tokens, or API keys.

## Documentation & Delivery

- **[TS-DOC-001]** Meet minimum exported-API doc coverage (see `profile.thresholds.yml`).
- **[TS-DELIV-001]** Keep PRs small and focused; rollback notes for risky changes.

## Desktop (Tauri)

- **[TS-DESK-001]** Pin Tauri CLI and Rust toolchain file (`rust-toolchain.toml`) in the desktop package.
- **[TS-DESK-002]** Rust in `src-tauri/` is formatted (`rustfmt`) and linted (`clippy -D warnings`) in CI.
- **[TS-DESK-003]** IPC commands are allowlisted; the webview must not receive filesystem paths outside the user-selected PDF or library roots.

## Governance

- **[TS-GOV-001]** Escalation SLA and quality exception authority follow the org process used by PY-GOV-001.
