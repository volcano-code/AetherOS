# Phase 1 — Hermes integration and ledger-backed task orchestration

## Goal

Run one real Hermes AIAgent turn through the AetherOS control plane, with task identity, execution identity, Hermes session identity, and immutable Harness digest correlated in the Event Ledger.

## Implemented in this phase-1 slice

- A subprocess adapter around the pinned Hermes public `run_agent.AIAgent` facade.
- A dedicated child worker using the configured Hermes Python interpreter and Hermes checkout.
- Operator-approved model-route allowlisting; a Harness cannot introduce arbitrary providers/models.
- Tools are intentionally disabled (`enabled_toolsets=[]`) in this first slice. This avoids ungoverned external side effects until the Effect Kernel is integrated into Hermes tool dispatch.
- Hermes memory and context-file loading are disabled in this first controlled smoke path; Personal Memory integration is a later phase.
- A ledger-backed TaskOrchestrator that persists task creation, planning/running/completion/failure, execution start, Hermes session start, and terminal execution facts.
- Recovery of orphaned RUNNING tasks as UNKNOWN/FAILED; no automatic replay.
- A deterministic fake-Hermes subprocess test, requiring no model credentials or network access.
- An explicit, billable local Hermes smoke script.

## Runtime architecture

~~~text
AetherOS TaskOrchestrator
        |
        | task_id / execution_id / user_id / Harness digest
        v
HermesRuntimeAdapter (async subprocess boundary)
        |
        | configured Hermes Python + pinned Hermes checkout
        v
worker.py
        |
        | public run_agent.AIAgent facade
        v
AIAgent.run_conversation(...)
        |
        +---- session_started event ----> AetherOS Event Ledger
        |
        +---- terminal result ----------> AetherOS Event Ledger
~~~

Hermes remains the only Agent Runtime. AetherOS does not implement an LLM loop or copy Hermes conversation transcripts. The ledger stores task/effect facts, the Hermes session ID, the Harness digest, and a response digest—not the raw assistant transcript.

## Configuration

Construct `HermesRuntimeConfig` with:

- `hermes_root`: path to the checked-out `vendor/hermes` directory.
- `python_executable`: Python interpreter from the Hermes PM environment (not necessarily the AetherOS virtualenv).
- `hermes_home`: optional Hermes user-data directory. If omitted, the child inherits the normal Hermes home resolution.
- `model_routes`: explicit allowlist mapping Harness route names to `ModelRoute(provider, model)`.
- `timeout_seconds` and `max_iterations`: bounded execution settings.

No API key is accepted in the Harness or task payload. The child inherits credentials from the configured environment/Hermes home.

## Local deterministic tests

~~~bash
python -m compileall -q aetheros scripts/aetheros_hermes_smoke.py
python -m unittest discover -s tests -v
~~~

These tests use a fake Hermes checkout and do not call a live model.

## Explicit live smoke test

The live smoke test can incur model-provider charges. Run it only after configuring Hermes credentials and selecting an approved model route.

~~~bash
export AETHEROS_HERMES_ROOT="$PWD/vendor/hermes"
export AETHEROS_HERMES_PYTHON="/path/to/hermes/pm/environment/bin/python"
# Optional: export HERMES_HOME="$HOME/.hermes"
export AETHEROS_HERMES_PROVIDER="your-configured-provider"
export AETHEROS_HERMES_MODEL="your-configured-model"

python scripts/aetheros_hermes_smoke.py
~~~

If the provider/model are already selected by Hermes configuration, the last two variables may be omitted and the `approved-default` route will defer to Hermes' configured defaults.

## Safety and current limitations

- No Hermes toolsets are exposed to the model in this phase-1 slice. This is deliberate; live tool execution must wait until the Effect Kernel wraps the actual dispatch boundary.
- The adapter uses a subprocess so Hermes' dependencies, module namespace, and lifecycle are isolated from the AetherOS API process.
- A worker timeout or failure after a Hermes session starts is recorded as UNKNOWN. It is not automatically retried.
- AetherOS records the response digest, not the raw response body, in the ledger.
- The local Event Ledger remains tamper-evident, not tamper-proof.
- The live Hermes smoke test and upstream Hermes test suite must be run in the user's configured local Hermes environment; GitHub CI only runs deterministic fake-runtime tests.
