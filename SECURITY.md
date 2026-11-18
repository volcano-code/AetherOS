# Security policy

## Controlled execution

AetherOS is a control plane. It must not grant an agent broader authority than the connected runtime already has.

### Phase 0 invariants

- No shell, filesystem, browser, network, or arbitrary code execution is implemented in this scaffold.
- No agent may autonomously modify Python source, model weights, security policy, approval rules, or permission boundaries.
- Harness candidates are data-only specifications, not executable code.
- Candidate promotion requires an explicit evaluation decision and human approval.
- High-impact external actions must be represented as approval-gated actions.
- Every approval decision must be attributable to a user and a specific action digest.

### Threat model to implement

- Prompt injection in retrieved content and tool outputs.
- Malicious or compromised MCP servers and Skills.
- Cross-user and cross-session data leakage.
- Memory poisoning and stale/conflicting memory.
- Unauthorized tool invocation and privilege escalation.
- Replay, duplicate execution, and task-resumption bugs.
- Secret exposure in logs, traces, and evaluation datasets.

### Reporting

Do not publish exploitable vulnerabilities or secrets in public issues. Use GitHub's private vulnerability reporting for security-sensitive findings.
