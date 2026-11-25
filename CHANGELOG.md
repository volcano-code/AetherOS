# Changelog

## Unreleased

### Added
- Initial AetherOS Phase 0 repository scaffold.
- Phase 1 isolated subprocess adapter for the pinned Hermes `run_agent.AIAgent` public facade.
- Ledger-backed TaskOrchestrator correlating task, execution, Hermes session, and Harness digests.
- Explicit live Hermes smoke script; model-visible toolsets remain disabled until Effect Kernel dispatch integration.
- Task state transition contract.
- Immutable, content-addressed Harness specification.
- Action-digest-bound human approval contract.
- Conservative controlled-RSI promotion gate.
- Hermes runtime adapter protocol and pinned submodule provenance.
- Agnes-inspired ADR for Event Ledger, Effect Sandwich, capability governance, and two-level RSI.
- SQLite hash-chained Event Ledger with deterministic replay and task projection.
- Effect Coordinator with durable intent, one-shot permit, settlement, UNKNOWN, and reconciliation states.
- Exact-digest capability trust and session version pin contracts.
- Session-scoped learning and evaluation-bound cross-task Playbook promotion.
- Deterministic fault-path tests for tampering, stale writers, permit reuse, crash recovery, and RSI promotion gates.
