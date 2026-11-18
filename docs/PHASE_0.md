# Phase 0 — repository bootstrap and baseline

## Scope

Phase 0 establishes provenance, a minimal testable control-plane contract, and a safe integration boundary. It does not implement production persistence or enable live tool execution.

## Completed in bootstrap

- [x] Verify the target GitHub repository is writable.
- [x] Create `main` bootstrap commit and `develop` branch.
- [x] Record upstream repository, observed SHAs, and MIT notice.
- [x] Add architecture, security, roadmap, and project scaffolding.
- [x] Add deterministic standard-library contract tests.
- [x] Add GitHub Actions CI; current contract-test workflow passes.
- [x] Define a pinned Hermes submodule integration at the observed upstream main commit.

## Remaining Phase 0 gates

- [ ] Confirm the Hermes gitlink is present and resolves to the pinned upstream commit.
- [ ] Clone with `--recurse-submodules` and verify the submodule checkout.
- [ ] Run Hermes' prescribed checks and test suite in its own isolated environment.
- [ ] Capture baseline test results and environment metadata.
- [ ] Inspect the latest stable tag and compare it with the pinned main snapshot.
- [ ] Generate a complete SBOM and audit licenses for selected extras/plugins/assets.
- [ ] Add CI for AetherOS contract tests and a separately scoped Hermes smoke test.
- [ ] Review the first architecture decision records before Phase 1.

## Exit criteria

Phase 0 exits only when upstream source provenance is reproducible, Hermes baseline checks are recorded, AetherOS contract tests pass, third-party notices are accurate, and the runtime adapter boundary is agreed.
