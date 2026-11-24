# Third-party notices

## NousResearch Hermes Agent

AetherOS uses NousResearch Hermes Agent as a pinned Git submodule at vendor/hermes.

- Source: https://github.com/NousResearch/hermes-agent
- License observed in upstream root: MIT
- Copyright: Copyright (c) 2025 Nous Research
- Reference commit: f7e2898aaefc8f967dbf7345e3999a65672fe60e

The submodule retains its upstream LICENSE, copyright notices, and Git history. AetherOS does not relicense those files.

## Agnes Harness — architectural reference only

AetherOS references selected public architecture ideas from Agnes Harness (AgnesAI-Labs/agnes-harness): append-only execution ledgers, explicit unknown-effect reconciliation, capability-aware version pinning, and two-level learning/refinement.

- Source: https://github.com/AgnesAI-Labs/agnes-harness
- Upstream license: Apache-2.0
- Usage in AetherOS: architecture reference only
- Copied Agnes source/package/runtime: none
- Runtime dependency: none

AetherOS independently implements its own Python contracts. No Agnes code or assets are vendored, and the Agnes license does not apply to AetherOS original code.

## Dependency and asset audit

The Phase 0 control-plane contracts use Python standard-library modules only. A complete dependency/SBOM and asset-license audit remains a release gate for selected Hermes extras/plugins and the future web application.
