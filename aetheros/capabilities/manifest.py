"""Declarative capability manifests; declarations are not OS sandbox enforcement."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


def _normalized(values: tuple[str, ...]) -> tuple[str, ...]:
    cleaned = tuple(sorted({value.strip() for value in values}))
    if any(not value for value in cleaned):
        raise ValueError("capability entries must be non-empty")
    return cleaned


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    plugin_id: str
    version: str
    network_hosts: tuple[str, ...] = ()
    filesystem_read: tuple[str, ...] = ()
    filesystem_write: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()
    model_access: bool = False
    child_agents: bool = False

    def __post_init__(self) -> None:
        if not self.plugin_id.strip() or not self.version.strip():
            raise ValueError("plugin_id and version must be non-empty")
        for field_name in ("network_hosts", "filesystem_read", "filesystem_write", "commands", "secrets"):
            object.__setattr__(self, field_name, _normalized(getattr(self, field_name)))

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin_id": self.plugin_id,
            "version": self.version,
            "network_hosts": list(self.network_hosts),
            "filesystem_read": list(self.filesystem_read),
            "filesystem_write": list(self.filesystem_write),
            "commands": list(self.commands),
            "secrets": list(self.secrets),
            "model_access": self.model_access,
            "child_agents": self.child_agents,
        }

    @property
    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
