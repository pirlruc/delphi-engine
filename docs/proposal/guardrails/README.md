# Proposed language packs for pirlruc/guardrails

These files are **proposals** for [pirlruc/guardrails](https://github.com/pirlruc/guardrails).
They are not pinned and CI must not read them as org defaults.

When Engineering Lead accepts them, copy each pack into the guardrails repo using the
three-file layout (`guardrails.md`, `profile.md`, `profile.thresholds.yml`), add `TS` to
the PACK table in the guardrails README, and cut a new guardrails tag. This workspace
then pins that tag at `docs/guardrails/` ([TOOL-002](../issues.yml)).

Until then Hermes desktop ([PROD-004](../issues.yml)) follows this proposal locally.
The Phase 1 Hermes CLI stays on the pinned Python pack.

| Pack | Prefix | Path |
| --- | --- | --- |
| TypeScript / React | `TS-*` | [`typescript/`](typescript/) |

Tauri’s Rust `src-tauri/` side is called out under `TS-DESK-*`. A future `RUST-*` pack
can absorb those rows; do not invent a second proposal pack until something else in
the org is Rust-first.
