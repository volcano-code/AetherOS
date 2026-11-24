"""Canonical, hash-chained event records for AetherOS task streams."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType
from typing import Any


def _json_value(value: Any) -> Any:
    """Convert supported data-only values into canonical JSON-compatible values."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("event payload object keys must be strings")
        return {key: _json_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported event payload type: {type(value).__name__}")


def freeze_json(value: Any) -> Any:
    """Deep-freeze JSON-compatible data for immutable event records."""
    normalized = _json_value(value)

    def freeze(item: Any) -> Any:
        if isinstance(item, dict):
            return MappingProxyType({key: freeze(val) for key, val in item.items()})
        if isinstance(item, list):
            return tuple(freeze(val) for val in item)
        return item

    return freeze(normalized)


def canonical_json(value: Any) -> str:
    """Deterministic AetherOS JSON profile; not a full RFC 8785/JCS implementation."""
    return json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def utc_timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("event timestamps must be timezone-aware")
    return current.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    stream_id: str
    sequence: int
    event_id: str
    event_type: str
    occurred_at: str
    actor_id: str
    payload: Mapping[str, Any]
    previous_hash: str
    event_hash: str

    def hash_body(self) -> dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "sequence": self.sequence,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "actor_id": self.actor_id,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
        }


def build_event(
    *,
    stream_id: str,
    sequence: int,
    event_id: str,
    event_type: str,
    actor_id: str,
    payload: Mapping[str, Any],
    previous_hash: str,
    occurred_at: datetime | None = None,
) -> LedgerEvent:
    for label, value in (
        ("stream_id", stream_id),
        ("event_id", event_id),
        ("event_type", event_type),
        ("actor_id", actor_id),
    ):
        if not value.strip():
            raise ValueError(f"{label} must be non-empty")
    if sequence < 1:
        raise ValueError("sequence must be >= 1")
    safe_payload = freeze_json(payload)
    timestamp = utc_timestamp(occurred_at)
    body = {
        "stream_id": stream_id,
        "sequence": sequence,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": timestamp,
        "actor_id": actor_id,
        "payload": safe_payload,
        "previous_hash": previous_hash,
    }
    digest = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    return LedgerEvent(
        stream_id=stream_id,
        sequence=sequence,
        event_id=event_id,
        event_type=event_type,
        occurred_at=timestamp,
        actor_id=actor_id,
        payload=safe_payload,
        previous_hash=previous_hash,
        event_hash=digest,
    )


def verify_event(event: LedgerEvent, expected_previous_hash: str, expected_sequence: int) -> None:
    if event.sequence != expected_sequence:
        raise ValueError(f"sequence gap: expected {expected_sequence}, got {event.sequence}")
    if event.previous_hash != expected_previous_hash:
        raise ValueError(f"previous hash mismatch at sequence {event.sequence}")
    actual = hashlib.sha256(canonical_json(event.hash_body()).encode("utf-8")).hexdigest()
    if actual != event.event_hash:
        raise ValueError(f"event hash mismatch at sequence {event.sequence}")
