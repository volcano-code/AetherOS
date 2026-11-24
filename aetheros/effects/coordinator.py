"""Effect Sandwich coordinator backed by durable ledger events.

The permit is consumed by appending effect.dispatch_started before calling an
external system. If the process then crashes, the outcome is conservatively
unknown and the same effect/permit is never automatically dispatched again.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from aetheros.ledger import GENESIS_HASH, SQLiteEventStore
from aetheros.security.approval import ApprovalRequest, ApprovalStatus
from .models import EffectSnapshot, EffectStatus

ReconciliationOutcome = Literal["succeeded", "failed", "not_applied"]


class EffectTransitionError(RuntimeError):
    """Raised for an invalid, stale, or replayed effect transition."""


def _snapshot_from_events(events, stream_id: str, effect_id: str) -> EffectSnapshot | None:
    current: EffectSnapshot | None = None
    for event in events:
        payload = event.payload
        if payload.get("effect_id") != effect_id:
            continue
        if event.event_type == "effect.intent_recorded":
            if current is not None:
                raise EffectTransitionError("duplicate effect intent")
            current = EffectSnapshot(
                stream_id=stream_id,
                effect_id=effect_id,
                action_digest=payload["action_digest"],
                status=EffectStatus.INTENT_RECORDED,
                idempotency_key=payload.get("idempotency_key"),
            )
        elif current is None:
            raise EffectTransitionError("effect event exists without an intent")
        elif event.event_type == "effect.permit_issued":
            if current.status is not EffectStatus.INTENT_RECORDED:
                raise EffectTransitionError("permit issued from an invalid state")
            if payload.get("action_digest") != current.action_digest:
                raise EffectTransitionError("permit digest does not match the durable intent")
            current = replace(
                current,
                status=EffectStatus.PERMITTED,
                permit_id=payload["permit_id"],
                approved_by=payload["approved_by"],
            )
        elif event.event_type == "effect.dispatch_started":
            if payload.get("action_digest") != current.action_digest:
                raise EffectTransitionError("dispatch digest does not match the durable intent")
            if current.status is not EffectStatus.PERMITTED or current.permit_id != payload.get("permit_id"):
                raise EffectTransitionError("dispatch started without the current one-shot permit")
            current = replace(current, status=EffectStatus.DISPATCH_STARTED)
        elif event.event_type == "effect.settled":
            if current.status is not EffectStatus.DISPATCH_STARTED:
                raise EffectTransitionError("settlement without a dispatch")
            target = EffectStatus.SUCCEEDED if payload["outcome"] == "succeeded" else EffectStatus.FAILED
            current = replace(
                current,
                status=target,
                result_digest=payload.get("result_digest"),
                external_reference=payload.get("external_reference"),
            )
        elif event.event_type == "effect.unknown":
            if current.status is not EffectStatus.DISPATCH_STARTED:
                raise EffectTransitionError("unknown outcome without a dispatch")
            current = replace(current, status=EffectStatus.UNKNOWN)
        elif event.event_type == "effect.reconciled":
            if current.status is not EffectStatus.UNKNOWN:
                raise EffectTransitionError("only unknown effects can be reconciled")
            outcome = payload["outcome"]
            target = {
                "succeeded": EffectStatus.RECONCILED_SUCCEEDED,
                "failed": EffectStatus.RECONCILED_FAILED,
                "not_applied": EffectStatus.RECONCILED_NOT_APPLIED,
            }[outcome]
            current = replace(
                current,
                status=target,
                reconciliation_actor=payload["reconciled_by"],
                external_reference=payload.get("external_reference"),
            )
        else:
            raise EffectTransitionError(f"unknown effect event type: {event.event_type}")
    return current


def _read(store: SQLiteEventStore, stream_id: str, effect_id: str):
    events = store.verify_stream(stream_id)
    snapshot = _snapshot_from_events(events, stream_id, effect_id)
    last_hash = events[-1].event_hash if events else GENESIS_HASH
    return snapshot, last_hash


class EffectCoordinator:
    """Coordinates intent, approval evidence, one-shot permit, dispatch and settlement."""

    def __init__(self, store: SQLiteEventStore) -> None:
        self.store = store

    def get(self, stream_id: str, effect_id: str) -> EffectSnapshot | None:
        return _read(self.store, stream_id, effect_id)[0]

    def record_intent(
        self, *, stream_id: str, effect_id: str, action_digest: str,
        actor_id: str, idempotency_key: str | None = None,
    ) -> EffectSnapshot:
        if not effect_id.strip() or not action_digest.strip():
            raise ValueError("effect_id and action_digest must be non-empty")
        if idempotency_key is not None and not idempotency_key.strip():
            raise ValueError("idempotency_key must be non-empty when supplied")
        current, last_hash = _read(self.store, stream_id, effect_id)
        if current is not None:
            raise EffectTransitionError("effect intent already exists; create a new effect_id for a new attempt")
        self.store.append(
            stream_id=stream_id,
            event_type="effect.intent_recorded",
            actor_id=actor_id,
            payload={
                "effect_id": effect_id,
                "action_digest": action_digest,
                "idempotency_key": idempotency_key,
            },
            event_id=f"effect-intent:{stream_id}:{effect_id}",
            expected_previous_hash=last_hash,
        )
        result = self.get(stream_id, effect_id)
        assert result is not None
        return result

    def issue_permit(
        self, *, stream_id: str, effect_id: str, action_digest: str,
        permit_id: str, approval: ApprovalRequest,
    ) -> EffectSnapshot:
        current, last_hash = _read(self.store, stream_id, effect_id)
        if current is None or current.status is not EffectStatus.INTENT_RECORDED:
            raise EffectTransitionError("permit can only be issued for a fresh intent")
        if current.action_digest != action_digest:
            raise EffectTransitionError("action digest mismatch")
        if not permit_id.strip():
            raise ValueError("permit_id must be non-empty")
        if approval.status is not ApprovalStatus.APPROVED:
            raise EffectTransitionError("a permit requires an approved decision receipt")
        if approval.action_digest != action_digest:
            raise EffectTransitionError("approval receipt is not bound to this exact action")
        if not approval.decided_by:
            raise EffectTransitionError("approval receipt has no authenticated decision actor")
        self.store.append(
            stream_id=stream_id,
            event_type="effect.permit_issued",
            actor_id=approval.decided_by,
            payload={
                "effect_id": effect_id,
                "action_digest": action_digest,
                "permit_id": permit_id,
                "approved_by": approval.decided_by,
                "approval_id": approval.request_id,
            },
            expected_previous_hash=last_hash,
        )
        result = self.get(stream_id, effect_id)
        assert result is not None
        return result

    def begin_dispatch(
        self, *, stream_id: str, effect_id: str, action_digest: str, permit_id: str,
        dispatcher_id: str,
    ) -> EffectSnapshot:
        current, last_hash = _read(self.store, stream_id, effect_id)
        if current is None or current.status is not EffectStatus.PERMITTED:
            raise EffectTransitionError("effect is not permitted or the one-shot permit was already consumed")
        if current.action_digest != action_digest or current.permit_id != permit_id:
            raise EffectTransitionError("permit is not bound to this exact action")
        self.store.append(
            stream_id=stream_id,
            event_type="effect.dispatch_started",
            actor_id=dispatcher_id,
            payload={
                "effect_id": effect_id,
                "action_digest": action_digest,
                "permit_id": permit_id,
            },
            expected_previous_hash=last_hash,
        )
        result = self.get(stream_id, effect_id)
        assert result is not None
        return result

    def settle(
        self, *, stream_id: str, effect_id: str, outcome: Literal["succeeded", "failed"],
        actor_id: str, result_digest: str | None = None,
        external_reference: str | None = None,
    ) -> EffectSnapshot:
        current, last_hash = _read(self.store, stream_id, effect_id)
        if current is None or current.status is not EffectStatus.DISPATCH_STARTED:
            raise EffectTransitionError("only an in-flight dispatch can be settled")
        if outcome not in ("succeeded", "failed"):
            raise ValueError("outcome must be succeeded or failed")
        self.store.append(
            stream_id=stream_id,
            event_type="effect.settled",
            actor_id=actor_id,
            payload={
                "effect_id": effect_id,
                "outcome": outcome,
                "result_digest": result_digest,
                "external_reference": external_reference,
            },
            expected_previous_hash=last_hash,
        )
        result = self.get(stream_id, effect_id)
        assert result is not None
        return result

    def mark_unknown(
        self, *, stream_id: str, effect_id: str, actor_id: str, reason_code: str,
    ) -> EffectSnapshot:
        current, last_hash = _read(self.store, stream_id, effect_id)
        if current is None or current.status is not EffectStatus.DISPATCH_STARTED:
            raise EffectTransitionError("only an in-flight dispatch can become unknown")
        if not reason_code.strip():
            raise ValueError("reason_code must be non-empty")
        self.store.append(
            stream_id=stream_id,
            event_type="effect.unknown",
            actor_id=actor_id,
            payload={"effect_id": effect_id, "reason_code": reason_code},
            expected_previous_hash=last_hash,
        )
        result = self.get(stream_id, effect_id)
        assert result is not None
        return result

    def reconcile_unknown(
        self, *, stream_id: str, effect_id: str, outcome: ReconciliationOutcome,
        reconciled_by: str, external_reference: str | None = None,
    ) -> EffectSnapshot:
        current, last_hash = _read(self.store, stream_id, effect_id)
        if current is None or current.status is not EffectStatus.UNKNOWN:
            raise EffectTransitionError("only an unknown effect can be reconciled")
        if outcome not in ("succeeded", "failed", "not_applied"):
            raise ValueError("invalid reconciliation outcome")
        if not reconciled_by.strip():
            raise ValueError("reconciled_by must be non-empty")
        self.store.append(
            stream_id=stream_id,
            event_type="effect.reconciled",
            actor_id=reconciled_by,
            payload={
                "effect_id": effect_id,
                "outcome": outcome,
                "reconciled_by": reconciled_by,
                "external_reference": external_reference,
            },
            expected_previous_hash=last_hash,
        )
        result = self.get(stream_id, effect_id)
        assert result is not None
        return result
