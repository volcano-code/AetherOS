# AetherOS architecture

## Product boundary

Hermes remains the only Agent Runtime: model interaction, native Agent Loop, tool execution, native Skills/MCP integration, memory provider interfaces, gateway, and existing execution backends.

AetherOS is the cross-session Personal Agent control plane. It coordinates tasks and specialist workers, tracks versioned Harness configurations, governs external effects, and runs controlled cross-task evaluation. It does not implement a second model/tool loop.

~~~text
Web / API / Automations
        |
AetherOS Control Plane
  | Personal Task Orchestrator
  | Supervisor / Agent Registry
  | Memory & Context Policies
  | Harness Registry / Skills Governance
  | Controlled RSI / Playbook Evaluation
        |
Evidence & Effect Kernel
  | Append-only Event Ledger
  | Task / Effect Projections
  | Intent -> Approval -> One-shot Permit
  | Settlement / Unknown Outcome / Reconciliation
  | Capability Trust / Session Version Pins
        |
Hermes Integration Adapter
        |
Hermes Agent Runtime (sole runtime)
        |
Hermes Tools / Skills / MCP / Subagents / Browser / Terminal / Providers
~~~

## State ownership

| State | Authority |
|---|---|
| Conversation messages, model/tool loop, Hermes session internals | Hermes |
| AetherOS task lifecycle and cross-agent orchestration facts | AetherOS Event Ledger |
| External effect intent, permit consumption, settlement, reconciliation | AetherOS Event Ledger |
| Current task status and UI timelines | Rebuildable projections of the AetherOS ledger |
| Harness specification and version digest | AetherOS Harness Registry |
| Capability review and session pin | AetherOS Capability Registry (initial contract; persistence follows) |
| Session-local learning | Session-scoped learning records |
| Global Playbook release | Human-approved, evaluation-bound release record |

Do not duplicate raw Hermes conversation transcripts into the AetherOS ledger. Store the Hermes session identifier and bounded references needed for task-level correlation.

## Evidence & Effect Kernel

### Event Ledger

The initial SQLite store is append-only through its API and keeps per-stream sequence numbers and a SHA-256 previous-hash chain. AetherOS task state and effect state are reconstructed from verified events. The current canonical JSON profile is deterministic for supported values but is not a complete RFC 8785 implementation. Local hash-chain verification is tamper-evidence, not protection against an attacker who can rewrite the entire database.

### Effect lifecycle

A durable intent precedes approval and dispatch. A one-shot permit is bound to an exact effect ID and action digest. The dispatch-started event consumes the permit before the external call. A timeout/disconnect after dispatch-started becomes UNKNOWN; the runtime must reconcile rather than automatically replay. This is not a universal exactly-once guarantee.

### Capability governance

Capability manifests describe requested access. Trust is bound to an exact manifest digest; sessions pin the reviewed version. A changed digest requires review and explicit migration. These declarations do not create OS sandbox isolation and must be backed by Hermes authorization and a real execution boundary.

### Two-level RSI

Session learning stays local to its source session. Cross-task Playbook candidates require evidence from multiple sessions/tasks and an evaluation bound to exact candidate/baseline/benchmark/OOD/model/budget identities. A candidate is only eligible for promotion after task-success, safety, OOD, sample-size, and human-approval gates.

## Architectural rules

1. Hermes is the sole Agent Runtime. Do not reimplement or replace its Agent Loop.
2. Use Hermes public APIs, plugins, Skills, and provider interfaces before changing upstream core.
3. Preserve prompt-cache invariants: do not mutate a live conversation's system prompt, tool surface, or historical context.
4. AetherOS task/effect facts have one authority: the Event Ledger. UI and task state are projections.
5. External effects are never blindly retried after an unknown outcome.
6. Capability declarations are not a sandbox; enforce permissions at the actual runtime boundary.
7. RSI candidates are declarative data, isolated during evaluation, and require human promotion.
8. Reproducibility requires recording model route, Harness digest, task/benchmark/OOD dataset versions, budget profile, and result digests.
9. Keep secrets and raw sensitive payloads out of the event ledger and traces.

## Current implementation boundary

The Phase 0.3 contracts provide a SQLite event store, hash verification, deterministic task projection, effect state machine, one-shot permit semantics, exact-digest capability review/pinning, and two-level Playbook promotion gates.

The Phase 1 integration slice adds an isolated subprocess adapter around the pinned Hermes `run_agent.AIAgent` public facade and a ledger-backed TaskOrchestrator. Task, execution, Hermes session, and Harness identities are correlated in the ledger. Model-visible toolsets are deliberately disabled in this first slice; the Effect Coordinator is not yet wired into live Hermes tool dispatch. The Capability Registry is currently in-memory. No production multi-user service, external API connector, OS sandbox, or live RSI worker is claimed.

## Deferred decisions

- Temporal vs. Hermes-native persistence orchestration: benchmark the integration before selecting.
- Graphiti/Neo4j: add only if relational/temporal memory tests show a measurable need.
- A2A: add after the internal Agent Registry and task contract are stable.
- Computer Use: Playwright/DOM first; visual fallback only for unsupported interfaces.
- External ledger anchoring/signatures: consider only when a threat model requires tamper evidence beyond local hash-chain verification.
