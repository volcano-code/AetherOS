import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from aetheros.harness import HarnessSpec
from aetheros.integrations.hermes import (
    HermesExecutionUnknown,
    HermesRunRequest,
    HermesRuntimeAdapter,
    HermesRuntimeConfig,
    ModelRoute,
)


FAKE_HERMES = r'''
import time

class AIAgent:
    def __init__(self, **kwargs):
        assert kwargs["enabled_toolsets"] == []
        assert kwargs["disabled_toolsets"] == []
        assert kwargs["skip_memory"] is True
        assert kwargs["skip_context_files"] is True
        self.session_id = "fake-hermes-session"
        self.model = kwargs.get("model") or "fake-default-model"
        print("Hermes diagnostic stdout must not corrupt the JSON protocol")

    def run_conversation(self, message, task_id=None):
        print("fake model turn started")
        if message == "__raise__":
            raise RuntimeError("synthetic failure after session creation")
        if message == "__sleep__":
            time.sleep(2)
        return {
            "final_response": "Hermes says: " + message,
            "failed": False,
            "interrupted": False,
        }

    def close(self):
        print("fake close diagnostic")
'''


class HermesAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hermes_root = Path(self.temp.name)
        (self.hermes_root / "run_agent.py").write_text(FAKE_HERMES, encoding="utf-8")
        self.config = HermesRuntimeConfig(
            hermes_root=self.hermes_root,
            python_executable=Path(sys.executable),
            model_routes={"approved-default": ModelRoute(provider="fake", model="fake-model")},
            timeout_seconds=10,
            max_iterations=3,
        )
        self.runtime = HermesRuntimeAdapter(self.config)
        self.harness = HarnessSpec("fake-harness", "Do not use tools.")
        self.request = HermesRunRequest(
            task_id="task-adapter",
            execution_id="execution-adapter",
            user_id="user-adapter",
            goal="test adapter",
            harness=self.harness,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_subprocess_adapter_correlates_session_and_result(self):
        started = []
        result = asyncio.run(self.runtime.run_task(self.request, on_session_started=started.append))
        self.assertEqual(started, ["fake-hermes-session"])
        self.assertEqual(result.session_id, "fake-hermes-session")
        self.assertEqual(result.final_response, "Hermes says: test adapter")
        self.assertEqual(result.model, "fake-model")
        self.assertEqual(len(result.response_digest), 64)

    def test_worker_error_after_session_is_unknown(self):
        request = HermesRunRequest(
            task_id="task-adapter",
            execution_id="execution-error",
            user_id="user-adapter",
            goal="__raise__",
            harness=self.harness,
        )
        started = []
        with self.assertRaises(HermesExecutionUnknown):
            asyncio.run(self.runtime.run_task(request, on_session_started=started.append))
        self.assertEqual(started, ["fake-hermes-session"])

    def test_unapproved_model_route_is_rejected_before_spawn(self):
        harness = HarnessSpec("other-route", "Prompt.", model_route="unapproved-route")
        request = HermesRunRequest("task", "exec", "user", "goal", harness)
        with self.assertRaisesRegex(Exception, "unapproved model route"):
            asyncio.run(self.runtime.run_task(request))


if __name__ == "__main__":
    unittest.main()
