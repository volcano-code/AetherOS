# Security policy

## Controlled execution

AetherOS is a control plane around Hermes Agent. It must not grant an agent broader authority than the connected runtime and authenticated principal already have.

## Phase 0 / Phase 0.3 invariants

- The current Event Ledger is a local tamper-evident hash chain, not tamper-proof storage. An attacker able to rewrite the complete database and hashes can defeat local verification.
- The Event Ledger stores task/effect metadata and digests, not credentials, raw secrets, or unbounded tool arguments.
- A dispatch-started event consumes the one-shot permit before an external call. If the outcome is uncertain, the effect becomes UNKNOWN and must not be automatically replayed.
- AetherOS does not claim exactly-once semantics for arbitrary external APIs. Use provider idempotency keys and reconciliation where available.
- The current Effect Coordinator is a tested control-plane contract and is not yet wired into live Hermes tool dispatch.
- Capability manifests are declarations and trust/version metadata. They are not OS sandbox enforcement and do not isolate arbitrary in-process plugin code.
- Capability Registry persistence and authenticated principal integration are not complete in this phase.
- Session learning cannot automatically publish a global Playbook. Cross-task promotion requires independent evaluation and explicit human approval.
- No agent may autonomously modify Python source, model weights, security policy, approval rules, or permission boundaries.
- Harness and Playbook candidates are declarative data; candidate content is never executed as code by the RSI evaluator.

## Threat model to implement

- Prompt injection in retrieved content and tool outputs.
- Malicious or compromised MCP servers and Skills.
- Cross-user and cross-session data leakage.
- Memory poisoning and stale/conflicting memory.
- Unauthorized tool invocation and privilege escalation.
- Replay, duplicate execution, and task-resumption bugs.
- Secret exposure in logs, traces, event payloads, and evaluation datasets.
- SQLite tampering, event deletion, sequence gaps, and concurrent writers.
- Crash between durable dispatch-started and external effect settlement.

## Reporting

Do not publish exploitable vulnerabilities or secrets in public issues. Use GitHub's private vulnerability reporting for security-sensitive findings.
