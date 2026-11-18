"""Stable runtime adapter protocol; avoids importing Hermes private internals in Phase 0."""

from typing import Protocol, Any


class HermesRuntime(Protocol):
    async def run_task(self, *, user_id: str, task_id: str, goal: str,
                       harness_digest: str) -> dict[str, Any]:
        """Execute one task using an immutable, preselected Harness version."""
        ...
