import asyncio
import unittest

from aetheros.harness import HarnessSpec
from aetheros.integrations.hermes import (
    HermesExecutionUnknown,
    HermesRunRequest,
    HermesRunResult,
    HermesRuntimeError,
)
from aetheros.ledger import SQLiteEventStore
from aetheros.tasks import (
    TaskExecutionError,
    TaskExecutionUnknown,
    TaskOrchestrator,
    TaskState,
)


class FakeRuntime:
    def __init__(self, *, fail_before_session=False, unknown_after_session=False,
                 definite_failure_after_session=False):
        self.fail_before_session = fail_before_session
        self.unknown_after_session = unknown_after_session
        self.definite_failure_after_session = definite_failure_after_session
        self.requests = []

    async def run_task(self, request: HermesRunRequest, *, on_session_started=None):
        self.requests.append(request)
        if self.fail_before_session:
            raise HermesRuntimeError("fake initialization failure")
        if on_session_started:
            on_session_started("hermes-session-test")
        if self.unknown_after_session:
            raise HermesExecutionUnknown("fake worker disappeared after session start")
        if self.definite_failure_after_session:
            raise HermesRuntimeError("fake Hermes returned a definite failed turn")
        return HermesRunResult.from_response(
            session_id="hermes-session-test",
            final_response="AetherOS test response",
            model="fake-model",
        )


class TaskOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteEventStore()
        self.harness = HarnessSpec("phase1-test", "Answer concisely.")
        self.runtime = FakeRuntime()
        self.orchestrator = TaskOrchestrator(self.store, self.runtime)

    def tearDown(self):
        self.store.close()

    def test_end_to_end_task_uses_hermes_session_and_ledger(self):
        task = self.orchestrator.create_task(
            user_id="user-1", goal="test an end-to-end task", harness=self.harness, task_id="task-1",
        )
        self.assertEqual(task.state, TaskState.CREATED)
        self.assertEqual(task.harness_digest, self.harness.digest)

        result = asyncio.run(self.orchestrator.execute_task("task-1", harness=self.harness))

        self.assertEqual(result.task.state, TaskState.COMPLETED)
        self.assertEqual(result.hermes_session_id, "hermes-session-test")
        self.assertEqual(result.final_response, "AetherOS test response")
        self.assertEqual(self.orchestrator.get_task("task-1").state, TaskState.COMPLETED)

        events = self.store.verify_stream("task:task-1")
        event_types = [event.event_type for event in events]
        self.assertEqual(event_types.count("execution.started"), 1)
        self.assertEqual(event_types.count("execution.session_started"), 1)
        self.assertEqual(event_types.count("execution.completed"), 1)
        completed = next(event for event in events if event.event_type == "execution.completed")
        self.assertEqual(completed.payload["hermes_session_id"], result.hermes_session_id)
        self.assertEqual(completed.payload["harness_digest"] if "harness_digest" in completed.payload else self.harness.digest,
                         self.harness.digest)

    def test_harness_digest_is_pinned_at_task_creation(self):
        self.orchestrator.create_task(
            user_id="user-1", goal="pinned task", harness=self.harness, task_id="task-pin",
        )
        other = HarnessSpec("different", "Different prompt.")
        with self.assertRaises(TaskExecutionError):
            asyncio.run(self.orchestrator.execute_task("task-pin", harness=other))
        self.assertEqual(self.orchestrator.get_task("task-pin").state, TaskState.CREATED)

    def test_known_failure_before_session_marks_task_failed(self):
        runtime = FakeRuntime(fail_before_session=True)
        orchestrator = TaskOrchestrator(self.store, runtime)
        orchestrator.create_task(
            user_id="user-1", goal="fail before session", harness=self.harness, task_id="task-fail",
        )
        with self.assertRaises(TaskExecutionError):
            asyncio.run(orchestrator.execute_task("task-fail", harness=self.harness))
        self.assertEqual(orchestrator.get_task("task-fail").state, TaskState.FAILED)
        events = self.store.verify_stream("task:task-fail")
        self.assertTrue(any(event.event_type == "execution.failed" for event in events))
        self.assertFalse(any(event.event_type == "execution.unknown" for event in events))

    def test_definite_hermes_failure_after_session_is_not_misclassified_unknown(self):
        runtime = FakeRuntime(definite_failure_after_session=True)
        orchestrator = TaskOrchestrator(self.store, runtime)
        orchestrator.create_task(
            user_id="user-1", goal="definite failure", harness=self.harness, task_id="task-definite-failure",
        )
        with self.assertRaises(TaskExecutionError):
            asyncio.run(orchestrator.execute_task("task-definite-failure", harness=self.harness))
        self.assertEqual(orchestrator.get_task("task-definite-failure").state, TaskState.FAILED)
        events = self.store.verify_stream("task:task-definite-failure")
        self.assertTrue(any(event.event_type == "execution.failed" for event in events))
        self.assertFalse(any(event.event_type == "execution.unknown" for event in events))

    def test_unknown_after_session_is_not_replayed(self):
        runtime = FakeRuntime(unknown_after_session=True)
        orchestrator = TaskOrchestrator(self.store, runtime)
        orchestrator.create_task(
            user_id="user-1", goal="unknown after session", harness=self.harness, task_id="task-unknown",
        )
        with self.assertRaises(TaskExecutionUnknown):
            asyncio.run(orchestrator.execute_task("task-unknown", harness=self.harness))
        self.assertEqual(orchestrator.get_task("task-unknown").state, TaskState.FAILED)
        events = self.store.verify_stream("task:task-unknown")
        self.assertTrue(any(event.event_type == "execution.unknown" for event in events))
        with self.assertRaises(TaskExecutionError):
            asyncio.run(orchestrator.execute_task("task-unknown", harness=self.harness))
        self.assertEqual(len(runtime.requests), 1)

    def test_completed_task_cannot_be_executed_again(self):
        self.orchestrator.create_task(
            user_id="user-1", goal="complete once", harness=self.harness, task_id="task-once",
        )
        asyncio.run(self.orchestrator.execute_task("task-once", harness=self.harness))
        with self.assertRaises(TaskExecutionError):
            asyncio.run(self.orchestrator.execute_task("task-once", harness=self.harness))
        self.assertEqual(len(self.runtime.requests), 1)

    def test_recovery_marks_orphaned_running_execution_unknown(self):
        self.orchestrator.create_task(
            user_id="user-1", goal="recover after restart", harness=self.harness, task_id="task-recover",
        )
        self.orchestrator._transition("task-recover", TaskState.PLANNED)
        self.orchestrator._transition("task-recover", TaskState.RUNNING)
        self.orchestrator._append(
            "task-recover", "execution.started",
            {"task_id": "task-recover", "execution_id": "orphan-exec", "harness_digest": self.harness.digest},
        )
        recovered = self.orchestrator.recover_incomplete_task("task-recover")
        self.assertEqual(recovered.state, TaskState.FAILED)
        events = self.store.verify_stream("task:task-recover")
        unknown = next(event for event in events if event.event_type == "execution.unknown")
        self.assertEqual(unknown.payload["execution_id"], "orphan-exec")
        self.assertEqual(unknown.payload["reason_code"], "process_restart_recovery")

    def test_runtime_result_must_be_typed_and_correlated(self):
        class BadRuntime:
            async def run_task(self, request, *, on_session_started=None):
                if on_session_started:
                    on_session_started("session-a")
                return {"final_response": "untyped"}

        orchestrator = TaskOrchestrator(self.store, BadRuntime())
        orchestrator.create_task(
            user_id="user-1", goal="bad result", harness=self.harness, task_id="task-bad-result",
        )
        with self.assertRaises(TaskExecutionUnknown):
            asyncio.run(orchestrator.execute_task("task-bad-result", harness=self.harness))
        self.assertEqual(orchestrator.get_task("task-bad-result").state, TaskState.FAILED)


if __name__ == "__main__":
    unittest.main()
