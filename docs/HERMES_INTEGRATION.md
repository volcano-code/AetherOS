# Hermes runtime integration

## Pinned source

AetherOS tracks Hermes as a Git submodule at:

- URL: https://github.com/NousResearch/hermes-agent.git
- Path: `vendor/hermes`
- Commit: `f7e2898aaefc8f967dbf7345e3999a65672fe60e`

The gitlink pins an exact upstream commit and preserves the upstream repository's Git history independently. This is intentionally not a copied source snapshot and does not create a GitHub Fork relationship.

## Clone

```bash
git clone --recurse-submodules https://github.com/volcano-code/AetherOS.git
cd AetherOS
git submodule status
```

For an existing clone:

```bash
git submodule update --init --recursive
```

## Update policy

Do not run `git submodule update --remote` in routine development. Update the pinned SHA only in a reviewed upstream-sync change after recording:

1. Previous and new Hermes commits.
2. Relevant upstream changelog and migration notes.
3. Upstream checks and AetherOS integration tests.
4. License/SBOM changes.

## Phase 0 validation

The pinned commit is a source provenance pin. The AetherOS CI does not claim to build Hermes or validate the full upstream test suite yet. Those checks must be run from `vendor/hermes` in a separately provisioned Hermes development environment.
