# AetherOS

**The Self-Evolving Personal Super Agent**

AetherOS is an open-source Personal Agent control plane built around a controlled, auditable Harness improvement loop. It is designed to integrate with [NousResearch/Hermes Agent](https://github.com/NousResearch/hermes-agent) as its agent runtime while keeping task orchestration, harness versioning, evaluation, approval, and audit concerns in an independently testable layer.

> Status: Phase 0 bootstrap. The initial repository is an integration/control-plane scaffold, not a vendored copy or GitHub fork of Hermes yet.

## Frozen project decisions

- Base runtime: Hermes Agent.
- Upstream reference: `NousResearch/hermes-agent`.
- Initial upstream reference commit: `f7e2898aaefc8f967dbf7345e3999a65672fe60e` (revalidate before integrating).
- Stable comparison tag: `v0.23.2`.
- Scope: Full.
- RSI mode: controlled Harness RSI only. No autonomous source-code edits, model-weight updates, or policy relaxation.
- Architecture: extension-first; preserve Hermes' prompt-cache, plugin, tool, and profile-isolation invariants.

## What lives here

- `aetheros/tasks`: durable task state model and transition validation.
- `aetheros/harness`: immutable, content-addressed Harness specifications.
- `aetheros/security`: explicit approval gates and auditable action policy.
- `aetheros/rsi`: offline candidate evaluation and promotion gates.
- `aetheros/integrations/hermes`: adapter boundary; no private Hermes internals are imported in the bootstrap.
- `tests`: deterministic, network-free contract tests.

## Development

Python 3.12+; runtime core currently uses only the Python standard library.

```bash
python -m unittest discover -s tests -v
python -m compileall -q aetheros
```

## Repository relationship

This repository is a standalone project (not a GitHub Fork). Hermes is now pinned as a Git submodule at `vendor/hermes`; clone with `--recurse-submodules`. The submodule retains upstream Git history and its own MIT license. AetherOS original files remain separately licensed. See `UPSTREAM.md` and `docs/HERMES_INTEGRATION.md`.

See:
- [Architecture](docs/ARCHITECTURE.md)
- [Phase 0 plan](docs/PHASE_0.md)
- [Upstream and licensing](UPSTREAM.md)
- [Security model](SECURITY.md)
- [Roadmap](ROADMAP.md)
