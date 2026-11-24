# Contributing

## Development setup

Requires Python 3.12+.

~~~bash
python -m compileall -q aetheros
python -m unittest discover -s tests -v
~~~

## Design rules

- Keep the AetherOS control plane separate from Hermes runtime internals.
- Hermes is the only Agent Runtime; do not implement a second model/tool loop.
- Prefer Hermes public interfaces, plugins, Skills, and MCP extensions.
- Keep Hermes conversation/session facts in Hermes; keep AetherOS task/effect facts in the AetherOS Event Ledger.
- Never mutate a running conversation's prompt/tool surface in a way that breaks upstream prompt-cache invariants.
- Event Ledger records are append-only through the public API and must pass hash-chain verification before replay.
- Never automatically replay an external effect whose outcome is UNKNOWN.
- Capability manifests are governance metadata, not proof of OS sandbox isolation.
- Harness/Playbook candidates are immutable declarative data, not executable patches.
- Session learning cannot directly publish a global Harness or Playbook change.
- Promotion requires reproducible independent evaluation and explicit human approval.
- Add deterministic tests for state transitions, authorization, concurrency, crash recovery, and evaluation gates.
- Preserve upstream and third-party notices when importing source or assets.

## Pull requests

Use focused branches and include purpose, design, tests, security implications, and migration notes.
