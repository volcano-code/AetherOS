"""Small, deterministic task-state contract; persistence is added in Phase 1."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum


class TaskState(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_EVENT = "waiting_event"
    RETRYING = "retrying"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


_ALLOWED: dict[TaskState, set[TaskState]] = {
    TaskState.CREATED: {TaskState.PLANNED, TaskState.CANCELLED},
    TaskState.PLANNED: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING: {
        TaskState.WAITING_APPROVAL, TaskState.WAITING_EVENT,
        TaskState.RETRYING, TaskState.FAILED, TaskState.COMPLETED,
        TaskState.CANCELLED,
    },
    TaskState.WAITING_APPROVAL: {
        TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED,
    },
    TaskState.WAITING_EVENT: {
        TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED,
    },
    TaskState.RETRYING: {TaskState.RUNNING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.FAILED: {TaskState.RETRYING, TaskState.CANCELLED},
    TaskState.COMPLETED: set(),
    TaskState.CANCELLED: set(),
}


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    user_id: str
    goal: str
    state: TaskState = TaskState.CREATED
    created_at: datetime = datetime.min.replace(tzinfo=timezone.utc)
    updated_at: datetime = datetime.min.replace(tzinfo=timezone.utc)
    harness_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.user_id.strip() or not self.goal.strip():
            raise ValueError("task_id, user_id, and goal must be non-empty")


def transition(task: Task, target: TaskState) -> Task:
    """Return a new task with a validated state transition."""
    if target not in _ALLOWED[task.state]:
        raise ValueError(f"invalid task transition: {task.state} -> {target}")
    return replace(task, state=target, updated_at=datetime.now(timezone.utc))
