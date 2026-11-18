"""Approval decisions bound to an exact action digest."""

from dataclasses import dataclass, replace
from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    request_id: str
    user_id: str
    action_digest: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None

    def __post_init__(self) -> None:
        if not all(x.strip() for x in (self.request_id, self.user_id, self.action_digest)):
            raise ValueError("approval identifiers and action_digest must be non-empty")


def decide(request: ApprovalRequest, *, actor_id: str, action_digest: str, approve: bool) -> ApprovalRequest:
    if request.status is not ApprovalStatus.PENDING:
        raise ValueError("approval request is already decided")
    if action_digest != request.action_digest:
        raise ValueError("action digest mismatch; approval cannot be replayed for another action")
    if not actor_id.strip():
        raise ValueError("actor_id must be non-empty")
    status = ApprovalStatus.APPROVED if approve else ApprovalStatus.DENIED
    return replace(request, status=status, decided_by=actor_id)
