"""Task projections rebuilt only from verified ledger events."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from aetheros.tasks.models import Task, TaskState, transition
from .models import LedgerEvent
from .store import SQLiteEventStore


@dataclass(frozen=True, slots=True)
class TaskProjection:
    task: Task | None = None
    last_sequence: int = 0


def reduce_task_projection(state: TaskProjection, event: LedgerEvent) -> TaskProjection:
    payload = event.payload
    if event.event_type == "task.created":
        if state.task is not None:
            raise ValueError("task.created can only appear once in a task stream")
        occurred_at = datetime.fromisoformat(event.occurred_at.replace("Z", "+00:00"))
        task = Task(
            task_id=str(payload["task_id"]),
            user_id=str(payload["user_id"]),
            goal=str(payload["goal"]),
            state=TaskState.CREATED,
            created_at=occurred_at,
            updated_at=occurred_at,
            harness_digest=str(payload["harness_digest"]) if payload.get("harness_digest") else None,
        )
        return TaskProjection(task=task, last_sequence=event.sequence)
    if event.event_type == "task.state_changed":
        if state.task is None:
            raise ValueError("task state cannot change before task.created")
        if str(payload["task_id"]) != state.task.task_id:
            raise ValueError("task_id mismatch in task stream")
        source = TaskState(str(payload["from_state"]))
        target = TaskState(str(payload["to_state"]))
        if state.task.state is not source:
            raise ValueError("task state transition does not match projected state")
        changed = transition(state.task, target)
        occurred_at = datetime.fromisoformat(event.occurred_at.replace("Z", "+00:00"))
        return TaskProjection(
            task=replace(changed, updated_at=occurred_at),
            last_sequence=event.sequence,
        )
    return replace(state, last_sequence=event.sequence)


def replay_task_projection(store: SQLiteEventStore, stream_id: str) -> TaskProjection:
    return store.replay(stream_id, reduce_task_projection, TaskProjection())
