"""Data-only Harness specs. This module deliberately does not execute candidate content."""

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HarnessSpec:
    name: str
    system_prompt: str
    tool_policy: dict[str, Any] = field(default_factory=dict)
    memory_policy: dict[str, Any] = field(default_factory=dict)
    skill_refs: tuple[str, ...] = ()
    subagent_policy: dict[str, Any] = field(default_factory=dict)
    workflow_policy: dict[str, Any] = field(default_factory=dict)
    model_route: str = "approved-default"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Harness name must be non-empty")
        if not self.model_route.strip():
            raise ValueError("model_route must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["skill_refs"] = list(self.skill_refs)
        return value

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())
