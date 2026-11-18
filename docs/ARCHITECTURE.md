# AetherOS architecture (Phase 0)

## Product boundary

Hermes remains the agent runtime: model interaction, its native agent loop, tools, Skills, memory/provider seams, gateway, and existing terminal backends. AetherOS adds an independently testable control plane around it.

```text
Web / API / Automations
        |
AetherOS Control Plane
  | Task Orchestrator
  | Agent Registry / Supervisor
  | User & Task Memory
  | Harness Registry
  | Controlled RSI + Evaluator
  | Approval / Audit Policy
        |
Hermes Integration Adapter
        |
Hermes Agent Runtime
        |
MCP / Skills / Browser / Terminal / Providers
```

## Architectural rules

1. Extension-first: use Hermes public APIs, plugins, skills, and provider interfaces before changing upstream core.
2. Prompt-cache safety: do not mutate a live conversation's system prompt, tool surface, or historical context. Apply Harness versions only at a new task/session boundary unless upstream explicitly supports a safe transition.
3. Control-plane ownership: AetherOS owns task identity, durable state, harness version identity, experiment metadata, promotion decisions, and audit records.
4. Runtime ownership: Hermes owns model/tool execution semantics. AetherOS must not duplicate its agent loop.
5. Data-only RSI: Phase 0–Phase 6 RSI proposals are declarative config changes. No arbitrary source execution.
6. Explicit trust boundaries: retrieved content is untrusted; tool permissions are checked by policy at execution time.
7. Reproducibility: every run records model/provider, harness digest, task dataset version, budget, and evaluation result.

## Planned packages

- `aetheros/tasks`: task states and transitions.
- `aetheros/harness`: immutable Harness specifications and content hashes.
- `aetheros/security`: approval and action policy contracts.
- `aetheros/rsi`: candidate comparison and promotion gates.
- `aetheros/integrations/hermes`: runtime adapter boundary.
- `apps/web`: later UI; not part of the Phase 0 runtime.

## Deferred decisions

- Temporal vs. Hermes-native persistence orchestration: benchmark integration before selecting.
- Graphiti/Neo4j: add only if relational/temporal memory tests show a measurable need.
- A2A: add after the internal Agent Registry and task contract are stable.
- Computer Use: Playwright/DOM first; visual computer-use fallback only for unsupported interfaces.
