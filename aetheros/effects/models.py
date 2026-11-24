"""Data contracts for external effects and conservative outcome handling."""

from dataclasses import dataclass
from enum import StrEnum


class EffectStatus(StrEnum):
    INTENT_RECORDED = "intent_recorded"
    PERMITTED = "permitted"
    DISPATCH_STARTED = "dispatch_started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    RECONCILED_SUCCEEDED = "reconciled_succeeded"
    RECONCILED_FAILED = "reconciled_failed"
    RECONCILED_NOT_APPLIED = "reconciled_not_applied"

    @property
    def terminal(self) -> bool:
        return self in {
            EffectStatus.SUCCEEDED,
            EffectStatus.FAILED,
            EffectStatus.RECONCILED_SUCCEEDED,
            EffectStatus.RECONCILED_FAILED,
            EffectStatus.RECONCILED_NOT_APPLIED,
        }


@dataclass(frozen=True, slots=True)
class EffectSnapshot:
    stream_id: str
    effect_id: str
    action_digest: str
    status: EffectStatus
    permit_id: str | None = None
    approved_by: str | None = None
    idempotency_key: str | None = None
    result_digest: str | None = None
    external_reference: str | None = None
    reconciliation_actor: str | None = None
