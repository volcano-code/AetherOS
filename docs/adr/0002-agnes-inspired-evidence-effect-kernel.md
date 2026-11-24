# ADR 0002: Evidence & Effect Kernel inspired by Agnes Harness

- Status: Accepted
- Date: 2026-11-24
- Scope: Architecture and control-plane contracts; implementation is incremental.

## Context

AetherOS uses Hermes Agent as its sole model/tool execution runtime. Agnes Harness (AgnesAI-Labs/agnes-harness) demonstrates several useful reliability patterns: an append-only execution ledger, explicit treatment of uncertain external effects, capability-aware plugin governance, version-pinned sessions, and a two-level learning/refinement process.

AetherOS should absorb these architectural ideas without introducing a second Agent Runtime or copying Agnes implementation code. Agnes is an architectural reference only; no Agnes source, package, or runtime is imported by this decision.

## Decisions

### 1. Hermes remains the only Agent Runtime

Hermes owns model interaction, its native Agent Loop, tool execution semantics, native Skills/MCP integration, memory provider interfaces, and runtime/session behavior.

AetherOS owns the cross-session control plane: user/task identity, orchestration state, Harness version identity, effect authorization records, cross-task Playbook governance, evaluation metadata, and audit projections.

AetherOS must not run a competing model/tool loop or duplicate Hermes conversation transcripts as a second source of truth.

### 2. Event Ledger is the authority for AetherOS task/effect facts

- Store task-level orchestration and external-effect events in per-task streams.
- Append events only through the store API; no update/delete API is provided.
- Each event has a stream sequence, event ID, actor, timestamp, canonical payload, previous hash, and SHA-256 event hash.
- Task state, execution timelines, approval views, and effect status are projections reconstructed from verified events.
- The initial canonical JSON profile sorts object keys, uses compact UTF-8 JSON, and rejects non-finite numbers. It is deterministic for the supported Python data model but is not claimed to be a full RFC 8785/JCS implementation.
- Hash chains are tamper-evident, not tamper-proof. An actor able to rewrite the complete database and all hashes can defeat local verification; external signed anchors are a later option.

Hermes remains authoritative for its own conversation/session records. AetherOS records task orchestration and effect facts, and references the Hermes session ID rather than duplicating every message.

### 3. External effects use an Effect Sandwich

The lifecycle is:

1. Record a durable intent containing an action digest and optional external idempotency key.
2. Obtain policy and approval evidence for that exact action.
3. Issue a one-shot permit bound to the effect ID and action digest.
4. Persist dispatch-started/permit-consumed before calling the external system.
5. Record a definite settlement, or mark the outcome unknown.
6. Reconcile unknown outcomes through an external query or an authorized human decision.

Unknown outcomes are never automatically replayed. A reconciled “not applied” result does not revive the old permit; a new attempt requires a new effect ID and fresh authorization.

This does not guarantee exactly-once behavior across arbitrary external systems. Use provider idempotency keys where supported and reconciliation where they are not. A crash after dispatch-started but before the external call is conservatively treated as unknown.

Raw secrets, credentials, and unbounded tool arguments must not be written into the ledger; store bounded metadata, digests, and external references.

### 4. Capability manifests are governance metadata, not a sandbox

AetherOS records plugin/connector capability declarations, reviews trust against the exact manifest digest, and pins a reviewed manifest version to a session. A changed digest requires explicit review and an explicit session migration.

A manifest does not itself constrain an in-process plugin or provide OS isolation. Runtime authorization must still be enforced by the Hermes tool policy and an actual supported sandbox/execution backend. Never describe a declaration-only check as a security boundary.

### 5. RSI has two levels

- Session-level learning produces scoped notes tied to one session. It cannot directly publish a global Harness change.
- Cross-task evolution proposes versioned, declarative Playbook candidates using evidence from multiple sessions/tasks. Each evaluation is bound to the exact candidate digest, baseline Harness digest, benchmark and OOD dataset digests, model route, and budget profile.

Promotion requires adequate sample counts, measurable task success improvement, no safety regression, bounded OOD regression, and explicit human approval. The initial numeric gate is a conservative engineering heuristic, not a statistical-significance claim; confidence intervals and larger sealed datasets are later evaluation work.

RSI may propose Prompt, Tool Guidance, Memory Policy, Skills, Playbooks, and workflow configuration changes. It may not autonomously modify source code, model weights, permissions, approval rules, or security policy.

## Consequences

- Add AetherOS-owned packages for ledger, effects, capability governance, and Playbook evolution.
- Keep these packages independent of Hermes private internals and model/tool loop implementation.
- Start with Python standard-library SQLite contracts; add durable multi-process services only after integration benchmarks justify them.
- Keep Agnes as an architecture reference only. No TypeScript runtime, MHS device protocol, or Agnes dependency is added.
- Phase 1 now includes ledger-backed task projections; Phase 1.5 adds the Effect Kernel before broad external tool automation.
