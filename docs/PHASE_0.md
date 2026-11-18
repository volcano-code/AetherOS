# Phase 0 — repository bootstrap and baseline

## Scope

Phase 0 establishes provenance, a minimal testable control-plane contract, and a safe integration boundary. It does not import the complete Hermes source tree, implement production persistence, or enable live tool execution.

## Completed in bootstrap commit

- [x] Verify the target GitHub repository is empty and writable.
- [x] Create `main` bootstrap commit and `develop` branch.
- [x] Record upstream repository, observed SHAs, and MIT notice.
- [x] Add architecture, security, roadmap, and project scaffolding.
- [x] Add deterministic standard-library contract tests.

## Remaining Phase 0 gates

- [ ] Clone and inspect the actual upstream checkout at the pinned commit.
- [ ] Run Hermes' prescribed checks and test suite in its own isolated environment.
- [ ] Capture baseline test results and environment metadata.
- [ ] Inspect the latest stable tag and compare it with the pinned main snapshot.
- [ ] Generate a complete SBOM and audit licenses for selected extras/plugins/assets.
- [ ] Decide import strategy (GitHub fork, subtree, or separately pinned runtime dependency) based on the repository's actual GitHub fork status and release/update requirements.
- [ ] Add CI for AetherOS contract tests.
- [ ] Review the first architecture decision records before Phase 1.

## Exit criteria

Phase 0 exits only when upstream source provenance is reproducible, Hermes baseline checks are recorded, AetherOS contract tests pass, third-party notices are accurate, and the runtime adapter boundary is agreed.
