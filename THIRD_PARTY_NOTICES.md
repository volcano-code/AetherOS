# Third-party notices

## NousResearch Hermes Agent

AetherOS is designed to integrate with NousResearch Hermes Agent.

- Source: https://github.com/NousResearch/hermes-agent
- License observed in upstream root: MIT
- Copyright: Copyright (c) 2025 Nous Research
- Reference commit: `f7e2898aaefc8f967dbf7345e3999a65672fe60e`

Hermes is included as a Git submodule at `vendor/hermes`, pinned to the reference commit in `UPSTREAM.md`. The submodule retains its upstream LICENSE, copyright notices, and Git history; AetherOS does not relicense those files.

## Dependency and asset audit

No third-party Python runtime dependencies are required by the Phase 0 control-plane scaffold. A complete dependency/SBOM and asset-license audit is a release gate for the upstream integration and web application phases.
