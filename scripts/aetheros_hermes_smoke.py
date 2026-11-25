#!/usr/bin/env python3
"""Explicit, billable smoke test against a locally configured Hermes runtime."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aetheros.harness import HarnessSpec
from aetheros.integrations.hermes import HermesRuntimeAdapter, HermesRuntimeConfig, ModelRoute
from aetheros.ledger import SQLiteEventStore
from aetheros.tasks import TaskOrchestrator


async def main() -> int:
    hermes_root = Path(os.environ["AETHEROS_HERMES_ROOT"]).expanduser().resolve()
    hermes_python = Path(os.environ.get("AETHEROS_HERMES_PYTHON", sys.executable)).expanduser().resolve()
    hermes_home = os.environ.get("HERMES_HOME")
    provider = os.environ.get("AETHEROS_HERMES_PROVIDER") or None
    model = os.environ.get("AETHEROS_HERMES_MODEL") or None
    db_path = Path(os.environ.get("AETHEROS_DB", "runs/aetheros-phase1-smoke.sqlite")).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    config = HermesRuntimeConfig(
        hermes_root=hermes_root,
        python_executable=hermes_python,
        hermes_home=Path(hermes_home) if hermes_home else None,
        model_routes={"approved-default": ModelRoute(provider=provider, model=model)},
        timeout_seconds=float(os.environ.get("AETHEROS_HERMES_TIMEOUT", "180")),
        max_iterations=int(os.environ.get("AETHEROS_HERMES_MAX_ITERATIONS", "8")),
    )
    harness = HarnessSpec(
        name="phase1-smoke",
        system_prompt="You are AetherOS running a controlled Hermes integration smoke test. "
                      "Answer the user's task directly and concisely.",
        model_route="approved-default",
    )
    with SQLiteEventStore(db_path) as store:
        orchestrator = TaskOrchestrator(store, HermesRuntimeAdapter(config))
        task = orchestrator.create_task(
            user_id=os.environ.get("AETHEROS_USER_ID", "local-user"),
            goal=os.environ.get("AETHEROS_SMOKE_PROMPT", "Reply with exactly: AETHEROS_HERMES_OK"),
            harness=harness,
        )
        result = await orchestrator.execute_task(task.task_id, harness=harness)
        print("task_id:", result.task.task_id)
        print("execution_id:", result.execution_id)
        print("hermes_session_id:", result.hermes_session_id)
        print("response_digest:", result.response_digest)
        print("final_response:")
        print(result.final_response)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
