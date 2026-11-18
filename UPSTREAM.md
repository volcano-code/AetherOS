# Upstream provenance and licensing

## Selected upstream

- Repository: https://github.com/NousResearch/hermes-agent
- Default branch observed: `main`
- Pinned source commit: `f7e2898aaefc8f967dbf7345e3999a65672fe60e` (observed 2026-11-18)
- Latest stable comparison tag observed: `v0.23.2`
- Stable tag commit: `ae2a81ccc00e9b7c06301523e5bb09608397149c`
- Upstream root license: MIT

Revalidate refs before every update. The pin is a reproducible source snapshot, not a promise that upstream main remains unchanged.

## Repository relationship

AetherOS is a standalone repository, not a GitHub Fork. Hermes is integrated as a Git submodule at `vendor/hermes`, pinned to the commit above. This preserves Hermes' complete upstream Git history independently and avoids copying a large upstream tree into AetherOS commits.

The submodule pointer is a Git gitlink (mode 160000). Clone with:

```bash
git clone --recurse-submodules https://github.com/volcano-code/AetherOS.git
```

For an existing checkout:

```bash
git submodule update --init --recursive
```

## License obligations

The inspected Hermes root LICENSE is MIT, copyright Nous Research (2025). The submodule retains its own upstream LICENSE and history. AetherOS' own LICENSE applies to original AetherOS files only; it does not relicense the Hermes submodule.

The Hermes root license does not establish the license of every bundled skill, plugin, model, frontend asset, or transitive dependency. Audit each selected component and generate an SBOM before redistribution.

## Sync policy

1. Update the gitlink only in a reviewed upstream-sync PR.
2. Record previous/new Hermes SHAs and relevant upstream changelog.
3. Run Hermes checks and AetherOS integration tests.
4. Review dependency, plugin, Skills, and asset license changes.
5. Never update to an unreviewed moving branch head automatically.
