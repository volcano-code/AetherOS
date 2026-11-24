# AetherOS Roadmap

## Frozen scope

- Base runtime: NousResearch Hermes Agent (sole Agent Runtime).
- Project scale: Full.
- RSI: controlled Harness and declarative Playbook optimization only.
- Product: Personal Super Agent with long-running tasks, memory, Skills, tools, dynamic specialist agents, and governed external actions.
- Agnes Harness: architectural reference for Event Ledger, Effect Sandwich, capability governance, version pinning, and two-level learning. No second runtime or Agnes code dependency.

## Phases

### Phase 0 — provenance and safe bootstrap
- Pin Hermes as a Git submodule and preserve its upstream license/history.
- Establish repository provenance, CI, architecture decisions, and deterministic contract tests.
- Run the Hermes upstream baseline in its own supported development environment.
- Complete selected dependency/SBOM/license audit.

### Phase 1 — Hermes integration and ledger-backed task core
- Implement the real Hermes Runtime Adapter through supported public interfaces.
- Establish task ID, AetherOS execution ID, and Hermes session ID correlation.
- Integrate SQLite Event Ledger into task lifecycle.
- Rebuild task state and execution timeline from verified event streams.
- Add compare-and-append concurrency protection and crash/reopen tests.
- Do not duplicate Hermes transcript or model/tool loop.

### Phase 1.5 — Evidence & Effect Kernel
- Integrate durable effect intent, policy/approval evidence, one-shot permit, dispatch-started, settlement, UNKNOWN, and reconciliation.
- Bind every permit to effect ID and action digest.
- Add provider idempotency keys where supported.
- Prevent automatic replay after an uncertain external effect.
- Wire the coordinator into one low-risk, testable external connector before expanding tool coverage.

### Phase 2 — Personal Memory and Context
- Integrate Hermes memory/provider capabilities rather than reimplementing memory storage.
- Add AetherOS user profile and task-context policy.
- Add session-scoped learning entries with evidence references and privacy controls.
- Add memory conflict, retention, correction, and user-control tests.

### Phase 3 — Harness, Skills, and capability governance
- Version Harness specifications and record immutable digests.
- Reuse Hermes Skills and MCP; add AetherOS trust review and session version pins.
- Require exact-digest review for changed capability manifests.
- Keep manifest declarations separate from actual OS sandbox enforcement.

### Phase 4 — Dynamic Multi-Agent orchestration
- Build Supervisor and specialist-worker contracts on top of Hermes SubAgents.
- Add task delegation, budgets, cancellation, independent review, and event correlation.
- Add A2A only after internal task/agent contracts are stable.
- Ensure each worker's external effects use the same Effect Kernel.

### Phase 5 — Always-on Personal Agent
- Add event-triggered and scheduled tasks using Hermes scheduling where appropriate.
- Add durable pause/resume and process-restart recovery.
- Add Browser/Playwright integration and event notifications.
- Reconcile uncertain external operations before any new dispatch.

### Phase 6 — Controlled two-level RSI
- Session-level learning remains scoped and cannot publish global Harness changes.
- Aggregate cross-task evidence into versioned declarative Playbook candidates.
- Run isolated probes on fixed tasks and sealed OOD sets.
- Bind evaluations to candidate, baseline, benchmark, OOD, model route, and budget digests.
- Require minimum evidence, no safety regression, bounded OOD regression, and human approval.
- Keep source-code/model-weight/security-policy modification out of scope.

### Phase 7 — Security, Evaluation, and Observability
- Add threat-model-driven prompt injection, malicious Skill/MCP, capability, replay, and memory-poisoning tests.
- Add crash/fault injection around dispatch and settlement.
- Add ledger integrity checks and privacy-safe traces.
- Measure task success, recovery, duplicate-effect prevention, latency, token cost, and OOD generalization.

### Phase 8 — Product delivery
- Deliver Personal Dashboard, Agent Workspace, Task Center, Memory Center, Skills/Integrations, Harness Lab, and Security Center.
- Add deployment, migrations, backup/restore, CI/CD, docs, demos, and benchmark report.
- Publish only after reproducible end-to-end acceptance tests pass.

## Non-goals for the initial release

- A second Agent Runtime alongside Hermes.
- Autonomous modification of source code or model weights.
- Unbounded autonomous operation.
- Unreviewed permission expansion.
- Claiming exactly-once effects for arbitrary third-party APIs.
- Treating capability manifests as OS sandbox enforcement.
- Adding frameworks solely to increase the technology count.
