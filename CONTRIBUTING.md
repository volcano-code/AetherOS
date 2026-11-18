# Contributing

## Development setup

Requires Python 3.12+.

```bash
python -m compileall -q aetheros
python -m unittest discover -s tests -v
```

## Design rules

- Keep the AetherOS control plane separate from Hermes runtime internals.
- Prefer upstream public interfaces, plugins, Skills, and MCP extensions.
- Never mutate a running conversation's prompt/tool surface in a way that breaks upstream prompt-cache invariants.
- Harness specs are immutable and declarative.
- RSI candidates cannot execute arbitrary code.
- Promotion requires independent evaluation and explicit approval.
- Add deterministic tests for state transitions, authorization, and evaluation gates.
- Preserve upstream and third-party notices when importing source or assets.

## Pull requests

Use focused branches and include purpose, design, tests, security implications, and migration notes.
