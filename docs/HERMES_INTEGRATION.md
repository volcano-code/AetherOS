# Hermes runtime integration

## Pinned source

AetherOS tracks Hermes as a Git submodule at:

- URL: https://github.com/NousResearch/hermes-agent.git
- Path: vendor/hermes
- Commit: f7e2898aaefc8f967dbf7345e3999a65672fe60e

The gitlink pins an exact upstream commit and preserves the upstream repository's Git history independently. This is intentionally not a copied source snapshot and does not create a GitHub Fork relationship.

## Runtime ownership

Hermes is the only Agent Runtime. It owns model interaction, the native Agent Loop, tool execution semantics, conversation/session persistence, native Skills/MCP integration, and its existing execution backends.

AetherOS must not create a second model/tool loop or copy Hermes transcripts into a competing conversation store. The Hermes adapter will correlate an AetherOS task/execution ID with the Hermes session ID.

AetherOS owns cross-session orchestration facts and external-effect governance:
- task lifecycle and agent delegation events;
- Harness and benchmark version identities;
- external effect intent, permit consumption, settlement, and reconciliation;
- cross-task Playbook evaluation and promotion records.

The AetherOS Event Ledger is not a replacement for Hermes session persistence. It stores task/effect facts and references to Hermes sessions.

## Clone

~~~bash
git clone --recurse-submodules https://github.com/volcano-code/AetherOS.git
cd AetherOS
git submodule status
~~~

For an existing clone:

~~~bash
git submodule update --init --recursive
~~~

## Update policy

Do not run git submodule update --remote in routine development. Update the pinned SHA only in a reviewed upstream-sync change after recording:

1. Previous and new Hermes commits.
2. Relevant upstream changelog and migration notes.
3. Upstream checks and AetherOS integration tests.
4. License/SBOM changes.

## Phase 1 adapter

AetherOS invokes the public `run_agent.AIAgent` facade in an isolated child process using the configured Hermes PM Python interpreter. The child calls `AIAgent.run_conversation(..., task_id=execution_id)` and emits a small JSON event protocol containing the Hermes session ID and terminal response. Hermes stdout is redirected away from the protocol stream.

The first integration deliberately passes `enabled_toolsets=[]`, `skip_memory=True`, and `skip_context_files=True`. This is a controlled model-only execution path; no external tools are exposed until the AetherOS Effect Kernel is integrated at the actual Hermes tool dispatch boundary. Model routing is selected from an operator-configured allowlist, not from arbitrary Harness input.

See [Phase 1](PHASE_1.md) for configuration and the explicit live smoke command.

## Phase 0 validation

The pinned commit is a source provenance pin. AetherOS CI verifies the gitlink metadata and runs deterministic adapter tests against a fake Hermes checkout; it does not claim to build Hermes or validate the full upstream test suite. Those checks and the live smoke test must be run from `vendor/hermes` in a separately provisioned Hermes developer environment.
