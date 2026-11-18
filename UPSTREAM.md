# Upstream provenance and licensing

## Selected upstream

- Repository: https://github.com/NousResearch/hermes-agent
- Default branch: `main`
- Reference commit observed on 2026-11-18: `f7e2898aaefc8f967dbf7345e3999a65672fe60e`
- Stable comparison tag observed: `v0.23.2`
- Stable tag commit: `ae2a81ccc00e9b7c06301523e5bb09608397149c`
- Upstream license: MIT

These SHAs are a research snapshot. Revalidate the upstream refs before every source import or sync.

## Repository relationship

AetherOS was initialized as a new, empty repository, not created through GitHub's fork endpoint. It therefore does not currently retain Hermes Git ancestry and does not contain Hermes source. The intended integration strategy is extension-first with an explicit upstream source import or a separately managed submodule/subtree decision after Phase 0 baseline validation.

Do not describe this repository as a fork until GitHub confirms the fork relationship. Do not claim upstream code is vendored until it is present and its provenance is recorded.

## License obligations

The inspected Hermes root LICENSE is MIT, copyright Nous Research (2025). When upstream source is imported, retain its LICENSE and copyright notices in the relevant files and include an attribution section here and in THIRD_PARTY_NOTICES.md.

The root license of Hermes does not establish the license of every bundled skill, plugin, model, frontend asset, or transitive dependency. Audit each imported component and produce an SBOM before redistribution.

## Sync policy

1. Record the exact upstream commit and tag in every import PR.
2. Prefer upstream bug fixes via reviewed cherry-picks or a controlled subtree update.
3. Keep AetherOS additions in clearly separated packages wherever possible.
4. Never overwrite upstream files blindly.
5. Re-run upstream checks and AetherOS contract tests after each sync.
