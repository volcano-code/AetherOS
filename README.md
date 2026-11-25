# AetherOS

**The Self-Evolving Personal Super Agent**

AetherOS is a Personal Agent control plane built around Hermes Agent as its sole execution runtime. It adds durable cross-session task orchestration, evidence-first external-effect governance, versioned Harness management, and controlled cross-task Playbook improvement.

> Status: Phase 1 integration slice. A subprocess adapter now invokes the pinned Hermes AIAgent public facade; the ledger-backed TaskOrchestrator correlates task, execution, Hermes session, and Harness identities. Model-visible toolsets remain disabled until the Effect Kernel is wired into Hermes tool dispatch. The capability registry is currently in-memory. AetherOS is not a GitHub Fork of Hermes.

## Frozen project decisions

- Base runtime: Hermes Agent (the only Agent Runtime).
- Upstream reference: NousResearch/hermes-agent, pinned at f7e2898aaefc8f967dbf7345e3999a65672fe60e.
- Scope: Full.
- RSI mode: controlled Harness/Playbook optimization only.
- Agnes Harness: architectural reference only; no Agnes source, package, or runtime is imported.
- Architecture: extension-first; preserve Hermes prompt-cache, plugin, tool, and profile-isolation invariants.

## Core architecture

- Event Ledger: append-only task/effect streams, sequence checks, SHA-256 hash chain, deterministic replay, and task projections.
- Effect Kernel: durable intent, action-bound one-shot permit, dispatch-started, settlement, UNKNOWN outcome, and explicit reconciliation. Unknown effects are never automatically replayed.
- Capability Governance: exact-manifest-digest trust and session version pins. Declarations are not an OS sandbox.
- Two-level RSI: session-scoped learning and cross-task declarative Playbook candidates requiring independent evaluation and human promotion.
- Hermes Adapter: a narrow integration boundary; AetherOS does not reimplement Hermes' Agent Loop or duplicate its conversation store.

## Repository layout

- aetheros/ledger: event records, SQLite store, integrity verification, replay, and projections.
- aetheros/effects: Effect Sandwich state machine and one-shot permit contracts.
- aetheros/capabilities: capability manifests, exact-digest trust, and session pins.
- aetheros/tasks: task domain state transitions.
- aetheros/harness: immutable, content-addressed Harness specifications.
- aetheros/rsi: baseline promotion gates and two-level Playbook evolution.
- aetheros/security: action-digest-bound approval contract.
- aetheros/integrations/hermes: isolated subprocess adapter and worker around Hermes AIAgent.
- aetheros/tasks/orchestrator.py: ledger-backed task execution and recovery.
- tests: deterministic, network-free contract and failure-path tests.

## Development

Python 3.12+; current AetherOS control-plane contracts use the standard library.

~~~bash
python -m compileall -q aetheros
python -m unittest discover -s tests -v
~~~

## Repository relationship

Hermes is pinned as a Git submodule at vendor/hermes; clone with --recurse-submodules. The submodule retains its upstream Git history and MIT license. AetherOS original files remain separately licensed. See UPSTREAM.md, docs/HERMES_INTEGRATION.md, and THIRD_PARTY_NOTICES.md.

## Phase 1 smoke test

See [Phase 1](docs/PHASE_1.md) for deterministic tests and the explicit live Hermes smoke command. The live command can incur model-provider charges; toolsets are disabled in this integration slice.

## Architecture and roadmap

- Architecture: docs/ARCHITECTURE.md
- Architecture decisions: docs/adr/
- Roadmap: ROADMAP.md
- Phase 0 gates: docs/PHASE_0.md
- Security model: SECURITY.md
