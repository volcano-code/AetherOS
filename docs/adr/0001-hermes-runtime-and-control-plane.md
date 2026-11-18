# ADR 0001: Hermes runtime with a separate AetherOS control plane

- Status: Accepted
- Date: 2026-11-18

## Context

Hermes already provides a mature agent loop, tools, Skills, memory interfaces, subagents, gateway, scheduling, and execution backends. Reimplementing these would create unnecessary divergence and risk breaking prompt-cache and plugin invariants.

## Decision

Use Hermes as the execution runtime and build AetherOS as a separate control plane responsible for user/task identity, task orchestration, Harness versioning, controlled RSI experiments, promotion decisions, and audit records.

## Consequences

- AetherOS does not fork or replace Hermes' agent loop in the Phase 0 scaffold.
- Integration must use stable public interfaces or a narrow adapter.
- Upstream source import and Git ancestry strategy remain explicit Phase 0 gates because this repository was created empty rather than through GitHub's Fork API.
- Harness candidates are immutable data, not executable patches.
