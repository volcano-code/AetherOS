# Phase 0 — repository bootstrap, provenance, and architecture contracts

## Scope

Phase 0 establishes reproducible Hermes provenance, a minimal testable AetherOS control plane, and explicit safety/ownership boundaries. It does not claim a production Hermes integration or live external tool dispatch.

## Completed in the repository

- [x] Initialize AetherOS repository and development branches.
- [x] Record Hermes upstream repository, MIT notice, and pinned submodule commit.
- [x] Add architecture, security, roadmap, and contribution documentation.
- [x] Add deterministic task, Harness, approval, and initial RSI contracts.
- [x] Add GitHub Actions for submodule-pin verification, compile, and contract tests.
- [x] Add Agnes-inspired architecture decision: Event Ledger, Effect Sandwich, capability governance, and two-level RSI.
- [x] Add SQLite hash-chained event store, task projection, Effect Coordinator, capability manifest/pinning contracts, and Playbook evaluation/promotion contracts.
- [x] Add deterministic failure-path tests for ledger tampering, stale writes, permit reuse, digest mismatch, unknown effects, restart recovery, capability version pinning, and RSI promotion gates.

## Remaining Phase 0 gates

- [ ] Clone AetherOS with submodules and verify the pinned Hermes checkout locally.
- [ ] Provision Hermes' supported PM developer environment and run the upstream checks/tests.
- [ ] Capture Hermes baseline test results and environment metadata.
- [ ] Complete selected dependency/SBOM/license audit for the runtime features we actually enable.
- [ ] Review and merge the Phase 0 integration PR chain.
- [ ] Confirm the Hermes adapter public-interface contract before Phase 1 implementation.

## Exit criteria

Phase 0 exits only when Hermes provenance is reproducible, the upstream baseline is recorded, AetherOS contract CI passes, selected dependency notices are accurate, and the runtime adapter boundary is agreed.

## Phase 0.3 implementation boundary

The new Event Ledger and Effect Coordinator are tested control-plane primitives. The Effect Coordinator is not yet connected to live Hermes tool dispatch. Capability review/pinning is currently in-memory. No production external-effect connector, persistent capability registry, production multi-user authorization, or live RSI worker is claimed.
