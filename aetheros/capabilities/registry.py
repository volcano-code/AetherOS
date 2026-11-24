"""Exact-digest trust and session capability pinning."""

from __future__ import annotations

from dataclasses import dataclass

from .manifest import CapabilityManifest
from aetheros.security.approval import ApprovalRequest, ApprovalStatus


class CapabilityAdmissionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TrustRecord:
    plugin_id: str
    version: str
    manifest_digest: str
    reviewed_by: str
    approved: bool


@dataclass(frozen=True, slots=True)
class CapabilityPin:
    session_id: str
    plugin_id: str
    version: str
    manifest_digest: str


class CapabilityRegistry:
    """In-memory Phase-0 registry; durable storage and runtime enforcement are later phases."""

    def __init__(self) -> None:
        self._trust: dict[tuple[str, str], TrustRecord] = {}
        self._pins: dict[tuple[str, str], CapabilityPin] = {}

    def review(self, manifest: CapabilityManifest, *, approval: ApprovalRequest) -> TrustRecord:
        expected_digest = f"sha256:{manifest.digest}"
        if approval.status is ApprovalStatus.PENDING or approval.action_digest != expected_digest:
            raise CapabilityAdmissionError("review decision must be final and bound to the exact manifest digest")
        if not approval.decided_by:
            raise CapabilityAdmissionError("review decision is missing a decision actor")
        record = TrustRecord(
            plugin_id=manifest.plugin_id,
            version=manifest.version,
            manifest_digest=manifest.digest,
            reviewed_by=approval.decided_by,
            approved=approval.status is ApprovalStatus.APPROVED,
        )
        self._trust[(manifest.plugin_id, manifest.digest)] = record
        return record

    def pin(self, session_id: str, manifest: CapabilityManifest) -> CapabilityPin:
        if not session_id.strip():
            raise ValueError("session_id must be non-empty")
        trust = self._trust.get((manifest.plugin_id, manifest.digest))
        if trust is None or not trust.approved:
            raise CapabilityAdmissionError("exact manifest digest has not been approved")
        key = (session_id, manifest.plugin_id)
        existing = self._pins.get(key)
        if existing is not None and existing.manifest_digest != manifest.digest:
            raise CapabilityAdmissionError("session is pinned to another manifest; explicit migration is required")
        pin = CapabilityPin(session_id, manifest.plugin_id, manifest.version, manifest.digest)
        self._pins[key] = pin
        return pin

    def get_pin(self, session_id: str, plugin_id: str) -> CapabilityPin | None:
        return self._pins.get((session_id, plugin_id))

    def migrate_pin(
        self, session_id: str, manifest: CapabilityManifest, *, approval: ApprovalRequest,
    ) -> CapabilityPin:
        expected_digest = f"sha256:{manifest.digest}"
        if approval.status is not ApprovalStatus.APPROVED or approval.action_digest != expected_digest:
            raise CapabilityAdmissionError("pin migration requires approval bound to the new manifest digest")
        if not approval.decided_by:
            raise CapabilityAdmissionError("migration approval is missing a decision actor")
        trust = self._trust.get((manifest.plugin_id, manifest.digest))
        if trust is None or not trust.approved:
            raise CapabilityAdmissionError("new manifest digest has not been approved")
        key = (session_id, manifest.plugin_id)
        if key not in self._pins:
            raise CapabilityAdmissionError("there is no existing session pin to migrate")
        pin = CapabilityPin(session_id, manifest.plugin_id, manifest.version, manifest.digest)
        self._pins[key] = pin
        return pin
