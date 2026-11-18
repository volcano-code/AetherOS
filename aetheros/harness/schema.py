"""Data-only, deeply immutable Harness specs; candidate content is never executed."""

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported Harness value type: {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (tuple, frozenset)):
        items = [_thaw(v) for v in value]
        return sorted(items, key=repr) if isinstance(value, frozenset) else items
    return value


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HarnessSpec:
    name: str
    system_prompt: str
    tool_policy: Mapping[str, Any] = field(default_factory=dict)
    memory_policy: Mapping[str, Any] = field(default_factory=dict)
    skill_refs: tuple[str, ...] = ()
    subagent_policy: Mapping[str, Any] = field(default_factory=dict)
    workflow_policy: Mapping[str, Any] = field(default_factory=dict)
    model_route: str = "approved-default"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Harness name must be non-empty")
        if not self.system_prompt.strip():
            raise ValueError("system_prompt must be non-empty")
        if not self.model_route.strip():
            raise ValueError("model_route must be non-empty")
        for name in ("tool_policy", "memory_policy", "subagent_policy", "workflow_policy"):
            object.__setattr__(self, name, _freeze(getattr(self, name)))
        object.__setattr__(self, "skill_refs", tuple(self.skill_refs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "system_prompt": self.system_prompt,
            "tool_policy": _thaw(self.tool_policy),
            "memory_policy": _thaw(self.memory_policy),
            "skill_refs": list(self.skill_refs),
            "subagent_policy": _thaw(self.subagent_policy),
            "workflow_policy": _thaw(self.workflow_policy),
            "model_route": self.model_route,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())
