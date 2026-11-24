# ADR 0001: Hermes runtime with a separate AetherOS control plane

- Status: Accepted
- Date: 2026-11-18

## Context

Hermes already provides a mature agent loop, tools, Skills, memory interfaces, subagents, gateway, scheduling, and execution backends. Reimplementing these would create unnecessary divergence and risk breaking prompt-cache and plugin invariants.

## Decision

Use Hermes as the sole execution runtime and build AetherOS as a separate control plane responsible for user/task identity, task orchestration, Harness versioning, controlled RSI experiments, promotion decisions, and audit records.

Hermes is pinned as a Git submodule at vendor/hermes. AetherOS remains a standalone repository rather than claiming GitHub Fork ancestry.

## Consequences

- AetherOS does not fork or replace Hermes' agent loop.
- Integration must use stable public interfaces or a narrow adapter.
- The Hermes submodule preserves upstream Git history and its MIT license.
- Harness candidates are immutable data, not executable patches.
- Event Ledger and Effect Kernel ownership is specified in ADR 0002.
