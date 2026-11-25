"""Ledger-backed task orchestration over the Hermes runtime contract."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
from typing import Callable
from uuid import uuid4

from aetheros.harness.schema import HarnessSpec
from aetheros.integrations.hermes.adapter import (
    HermesExecutionUnknown,
    HermesRunRequest,
    HermesRunResult,
    HermesRuntime,
    HermesRuntimeError,
)
from aetheros.ledger import GENESIS_HASH, SQLiteEventStore
from aetheros.ledger.projections import replay_task_projection
from aetheros.tasks.models import Task, TaskState, transition


class TaskNotFoundError(LookupError):
    pass


class TaskExecutionError(RuntimeError):
    pass


class TaskExecutionUnknown(TaskExecutionError):
    """The runtime started but no terminal result was durably confirmed."""


@dataclass(frozen=True, slots=True)
class TaskExecutionResult:
    task: Task
    execution_id: str
    hermes_session_id: str
    final_response: str
    response_digest: str
    model: str | None


class TaskOrchestrator:
    """Coordinates one task without reimplementing Hermes' Agent Loop.

    Task state is always rebuilt from the Event Ledger. The Hermes runtime is
    injected behind a narrow protocol, which makes offline tests deterministic.
    """

    def __init__(self, store: SQLiteEventStore, runtime: HermesRuntime, *, actor_id: str = "aetheros") -> None:
        if not actor_id.strip():
            raise ValueError("actor_id must be non-empty")
        self.store = store
        self.runtime = runtime
        self.actor_id = actor_id

    @staticmethod
    def stream_id(task_id: str) -> str:
        return f"task:{task_id}"

    def create_task(
        self,
        *,
        user_id: str,
        goal: str,
        harness: HarnessSpec,
        task_id: str | None = None,
    ) -> Task:
        task_id = task_id or str(uuid4())
        if not task_id.strip() or not user_id.strip() or not goal.strip():
            raise ValueError("task_id, user_id, and goal must be non-empty")
        stream_id = self.stream_id(task_id)
        if self.store.verify_stream(stream_id):
            raise ValueError(f"task already exists: {task_id}")
        self.store.append(
            stream_id=stream_id,
            event_type="task.created",
            event_id=f"task-created:{task_id}",
            actor_id=user_id,
            payload={
                "task_id": task_id,
                "user_id": user_id,
                "goal": goal,
                "harness_digest": harness.digest,
            },
            expected_previous_hash=GENESIS_HASH,
        )
        task = self.get_task(task_id)
        assert task is not None
        return task

    def get_task(self, task_id: str) -> Task | None:
        projection = replay_task_projection(self.store, self.stream_id(task_id))
        return projection.task

    def _last_hash(self, stream_id: str) -> str:
        events = self.store.verify_stream(stream_id)
        return events[-1].event_hash if events else GENESIS_HASH

    def _append(self, task_id: str, event_type: str, payload: dict, *, actor_id: str | None = None) -> None:
        stream_id = self.stream_id(task_id)
        self.store.append(
            stream_id=stream_id,
            event_type=event_type,
            actor_id=actor_id or self.actor_id,
            payload=payload,
            expected_previous_hash=self._last_hash(stream_id),
        )

    def _transition(self, task_id: str, target: TaskState) -> Task:
        task = self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        next_task = transition(task, target)
        self._append(
            task_id,
            "task.state_changed",
            {
                "task_id": task_id,
                "from_state": task.state.value,
                "to_state": next_task.state.value,
            },
        )
        result = self.get_task(task_id)
        assert result is not None
        return result

    async def execute_task(self, task_id: str, *, harness: HarnessSpec) -> TaskExecutionResult:
        task = self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task.harness_digest != harness.digest:
            raise TaskExecutionError("the supplied Harness does not match the task's pinned digest")
        if task.state is TaskState.CREATED:
            task = self._transition(task_id, TaskState.PLANNED)
        if task.state is not TaskState.PLANNED:
            raise TaskExecutionError(f"task is not executable from state {task.state.value}")

        task = self._transition(task_id, TaskState.RUNNING)
        execution_id = str(uuid4())
        self._append(
            task_id,
            "execution.started",
            {
                "task_id": task_id,
                "execution_id": execution_id,
                "harness_digest": harness.digest,
                "model_route": harness.model_route,
            },
        )
        session_id: str | None = None

        def on_session_started(value: str) -> None:
            nonlocal session_id
            if not isinstance(value, str) or not value.strip():
                raise TaskExecutionError("Hermes runtime supplied an invalid session_id")
            if session_id is not None:
                if session_id != value:
                    raise TaskExecutionError("Hermes runtime changed session_id within one execution")
                return
            session_id = value
            self._append(
                task_id,
                "execution.session_started",
                {"task_id": task_id, "execution_id": execution_id, "hermes_session_id": value},
            )

        request = HermesRunRequest(
            task_id=task_id,
            execution_id=execution_id,
            user_id=task.user_id,
            goal=task.goal,
            harness=harness,
        )
        try:
            result = await self.runtime.run_task(request, on_session_started=on_session_started)
            if not isinstance(result, HermesRunResult):
                raise TypeError("Hermes runtime must return HermesRunResult")
            if session_id is None:
                on_session_started(result.session_id)
            elif session_id != result.session_id:
                raise TaskExecutionError("Hermes result session_id does not match the started session")
            if not result.final_response.strip():
                raise TaskExecutionError("Hermes returned an empty final response")
            expected_digest = hashlib.sha256(result.final_response.encode("utf-8")).hexdigest()
            if expected_digest != result.response_digest:
                raise TaskExecutionError("Hermes response digest validation failed")
            self._append(
                task_id,
                "execution.completed",
                {
                    "task_id": task_id,
                    "execution_id": execution_id,
                    "hermes_session_id": result.session_id,
                    "response_digest": result.response_digest,
                    "harness_digest": harness.digest,
                    "model": result.model,
                },
            )
            completed_task = self._transition(task_id, TaskState.COMPLETED)
            return TaskExecutionResult(
                task=completed_task,
                execution_id=execution_id,
                hermes_session_id=result.session_id,
                final_response=result.final_response,
                response_digest=result.response_digest,
                model=result.model,
            )
        except asyncio.CancelledError:
            self._mark_unknown(task_id, execution_id, session_id, "orchestrator_cancelled")
            raise
        except (HermesExecutionUnknown, asyncio.TimeoutError) as exc:
            self._mark_unknown(task_id, execution_id, session_id, type(exc).__name__)
            raise TaskExecutionUnknown("task execution ended without a confirmed terminal result") from exc
        except HermesRuntimeError as exc:
            self._mark_failed(task_id, execution_id, type(exc).__name__)
            raise TaskExecutionError("Hermes reported a definite runtime/turn failure") from exc
        except Exception as exc:
            if session_id is not None:
                self._mark_unknown(task_id, execution_id, session_id, type(exc).__name__)
                raise TaskExecutionUnknown(
                    "Hermes session started but AetherOS could not confirm a terminal result"
                ) from exc
            self._mark_failed(task_id, execution_id, type(exc).__name__)
            raise TaskExecutionError("Hermes task execution failed before session start") from exc

    def _terminal_event_type(self, task_id: str, execution_id: str) -> str | None:
        terminal_types = {"execution.completed", "execution.failed", "execution.unknown"}
        for event in reversed(self.store.verify_stream(self.stream_id(task_id))):
            if event.payload.get("execution_id") == execution_id and event.event_type in terminal_types:
                return event.event_type
        return None

    def _mark_failed(self, task_id: str, execution_id: str, error_type: str) -> None:
        if self._terminal_event_type(task_id, execution_id) is not None:
            return
        self._append(
            task_id,
            "execution.failed",
            {"task_id": task_id, "execution_id": execution_id, "error_type": error_type},
        )
        task = self.get_task(task_id)
        if task is not None and task.state is TaskState.RUNNING:
            self._transition(task_id, TaskState.FAILED)

    def _mark_unknown(
        self, task_id: str, execution_id: str, session_id: str | None, reason_code: str
    ) -> None:
        if self._terminal_event_type(task_id, execution_id) is not None:
            return
        self._append(
            task_id,
            "execution.unknown",
            {
                "task_id": task_id,
                "execution_id": execution_id,
                "hermes_session_id": session_id,
                "reason_code": reason_code,
            },
        )
        task = self.get_task(task_id)
        if task is not None and task.state is TaskState.RUNNING:
            self._transition(task_id, TaskState.FAILED)

    def recover_incomplete_task(self, task_id: str, *, actor_id: str = "recovery") -> Task:
        """Mark an orphaned RUNNING execution UNKNOWN; never silently replay it."""
        task = self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task.state is not TaskState.RUNNING:
            raise TaskExecutionError(f"task is not running: {task.state.value}")
        events = self.store.verify_stream(self.stream_id(task_id))
        active_execution: str | None = None
        session_id: str | None = None
        terminal_types = {"execution.completed", "execution.failed", "execution.unknown"}
        terminal_by_id = {
            str(event.payload.get("execution_id")): event.event_type
            for event in events
            if event.event_type in terminal_types and event.payload.get("execution_id")
        }
        latest_execution: str | None = None
        for event in events:
            if event.event_type == "execution.started":
                candidate = event.payload.get("execution_id")
                if candidate:
                    latest_execution = str(candidate)
                    if latest_execution not in terminal_by_id:
                        active_execution = latest_execution
            elif event.event_type == "execution.session_started" and event.payload.get("execution_id") == active_execution:
                session_id = str(event.payload.get("hermes_session_id") or "") or None
        if active_execution is None:
            terminal = terminal_by_id.get(latest_execution or "")
            if terminal == "execution.completed":
                return self._transition(task_id, TaskState.COMPLETED)
            if terminal in {"execution.failed", "execution.unknown"}:
                return self._transition(task_id, TaskState.FAILED)
            raise TaskExecutionError("RUNNING task has no non-terminal execution record")
        self._append(
            task_id,
            "execution.unknown",
            {
                "task_id": task_id,
                "execution_id": active_execution,
                "hermes_session_id": session_id,
                "reason_code": "process_restart_recovery",
            },
            actor_id=actor_id,
        )
        return self._transition(task_id, TaskState.FAILED)
