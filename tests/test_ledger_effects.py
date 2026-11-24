import sqlite3
import tempfile
import unittest
from pathlib import Path

from aetheros.effects import EffectCoordinator, EffectStatus, EffectTransitionError
from aetheros.ledger import ConcurrentAppendError, LedgerIntegrityError, SQLiteEventStore
from aetheros.ledger.projections import replay_task_projection
from aetheros.tasks.models import TaskState


class LedgerTests(unittest.TestCase):
    def test_append_verify_and_replay(self):
        with SQLiteEventStore() as store:
            store.append(stream_id="task-1", event_type="task.created", actor_id="user-1",
                         payload={"task_id": "task-1", "user_id": "user-1", "goal": "research"})
            store.append(stream_id="task-1", event_type="task.state_changed", actor_id="system",
                         payload={"task_id": "task-1", "from_state": "created", "to_state": "planned"})
            events = store.verify_stream("task-1")
            self.assertEqual([event.sequence for event in events], [1, 2])
            projection = replay_task_projection(store, "task-1")
            replayed_again = replay_task_projection(store, "task-1")
            self.assertEqual(projection.task.state, TaskState.PLANNED)
            self.assertEqual(projection.last_sequence, 2)
            self.assertEqual(projection.task.updated_at, replayed_again.task.updated_at)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ledger.sqlite"
            store = SQLiteEventStore(db)
            store.append(stream_id="task-1", event_type="task.created", actor_id="user-1",
                         payload={"task_id": "task-1", "user_id": "user-1", "goal": "research"})
            store.close()
            connection = sqlite3.connect(db)
            connection.execute(
                "UPDATE ledger_events SET payload_json = ? WHERE stream_id = ? AND sequence = 1",
                ('{"goal":"tampered","task_id":"task-1","user_id":"user-1"}', "task-1"),
            )
            connection.commit()
            connection.close()
            reopened = SQLiteEventStore(db)
            with self.assertRaises(LedgerIntegrityError):
                reopened.verify_stream("task-1")
            reopened.close()

    def test_compare_and_append_rejects_stale_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ledger.sqlite"
            first = SQLiteEventStore(db)
            second = SQLiteEventStore(db)
            first.append(stream_id="task-1", event_type="task.created", actor_id="user",
                         payload={"task_id": "task-1", "user_id": "user", "goal": "x"})
            stale_hash = first.verify_stream("task-1")[-1].event_hash
            second.append(stream_id="task-1", event_type="task.note", actor_id="agent", payload={"note": "new"})
            with self.assertRaises(ConcurrentAppendError):
                first.append(
                    stream_id="task-1", event_type="task.note", actor_id="agent",
                    payload={"note": "stale"}, expected_previous_hash=stale_hash,
                )
            first.close()
            second.close()

    def test_event_payload_is_deeply_immutable(self):
        with SQLiteEventStore() as store:
            event = store.append(stream_id="s", event_type="test", actor_id="a",
                                 payload={"nested": {"value": 1}})
            with self.assertRaises(TypeError):
                event.payload["nested"]["value"] = 2


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteEventStore()
        self.effects = EffectCoordinator(self.store)
        self.base = dict(
            stream_id="task-1", effect_id="github-issue-1",
            action_digest="sha256:action-001", actor_id="agent",
        )

    def tearDown(self):
        self.store.close()

    def _permitted(self):
        self.effects.record_intent(**self.base, idempotency_key="idem-001")
        return self.effects.issue_permit(
            stream_id="task-1", effect_id="github-issue-1",
            action_digest="sha256:action-001", permit_id="permit-1", approved_by="user-1",
        )

    def test_one_shot_permit_and_settlement(self):
        self._permitted()
        started = self.effects.begin_dispatch(
            stream_id="task-1", effect_id="github-issue-1", action_digest="sha256:action-001",
            permit_id="permit-1", dispatcher_id="worker-1",
        )
        self.assertEqual(started.status, EffectStatus.DISPATCH_STARTED)
        with self.assertRaises(EffectTransitionError):
            self.effects.begin_dispatch(
                stream_id="task-1", effect_id="github-issue-1", action_digest="sha256:action-001",
                permit_id="permit-1", dispatcher_id="worker-1",
            )
        settled = self.effects.settle(
            stream_id="task-1", effect_id="github-issue-1", outcome="succeeded",
            actor_id="worker-1", external_reference="issue#42",
        )
        self.assertEqual(settled.status, EffectStatus.SUCCEEDED)

    def test_wrong_action_digest_cannot_receive_or_consume_permit(self):
        self.effects.record_intent(**self.base)
        with self.assertRaises(EffectTransitionError):
            self.effects.issue_permit(
                stream_id="task-1", effect_id="github-issue-1", action_digest="sha256:other",
                permit_id="permit-1", approved_by="user-1",
            )

    def test_unknown_outcome_is_never_automatically_replayed(self):
        self._permitted()
        self.effects.begin_dispatch(
            stream_id="task-1", effect_id="github-issue-1", action_digest="sha256:action-001",
            permit_id="permit-1", dispatcher_id="worker-1",
        )
        unknown = self.effects.mark_unknown(
            stream_id="task-1", effect_id="github-issue-1", actor_id="system", reason_code="timeout_after_send",
        )
        self.assertEqual(unknown.status, EffectStatus.UNKNOWN)
        with self.assertRaises(EffectTransitionError):
            self.effects.begin_dispatch(
                stream_id="task-1", effect_id="github-issue-1", action_digest="sha256:action-001",
                permit_id="permit-1", dispatcher_id="recovery-worker",
            )
        reconciled = self.effects.reconcile_unknown(
            stream_id="task-1", effect_id="github-issue-1", outcome="not_applied", reconciled_by="operator-1",
        )
        self.assertEqual(reconciled.status, EffectStatus.RECONCILED_NOT_APPLIED)
        with self.assertRaises(EffectTransitionError):
            self.effects.begin_dispatch(
                stream_id="task-1", effect_id="github-issue-1", action_digest="sha256:action-001",
                permit_id="permit-1", dispatcher_id="recovery-worker",
            )

    def test_duplicate_intent_is_rejected(self):
        self.effects.record_intent(**self.base)
        with self.assertRaises(EffectTransitionError):
            self.effects.record_intent(**self.base)

    def test_dispatch_started_survives_restart_as_unsettled(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "effects.sqlite"
            store = SQLiteEventStore(db)
            effects = EffectCoordinator(store)
            effects.record_intent(
                stream_id="task-r", effect_id="effect-r", action_digest="sha256:r", actor_id="agent",
            )
            effects.issue_permit(
                stream_id="task-r", effect_id="effect-r", action_digest="sha256:r",
                permit_id="permit-r", approved_by="user",
            )
            effects.begin_dispatch(
                stream_id="task-r", effect_id="effect-r", action_digest="sha256:r",
                permit_id="permit-r", dispatcher_id="worker",
            )
            store.close()
            reopened = SQLiteEventStore(db)
            recovered = EffectCoordinator(reopened)
            self.assertEqual(recovered.get("task-r", "effect-r").status, EffectStatus.DISPATCH_STARTED)
            recovered.mark_unknown(
                stream_id="task-r", effect_id="effect-r", actor_id="recovery",
                reason_code="process_restarted_before_settlement",
            )
            with self.assertRaises(EffectTransitionError):
                recovered.begin_dispatch(
                    stream_id="task-r", effect_id="effect-r", action_digest="sha256:r",
                    permit_id="permit-r", dispatcher_id="recovery",
                )
            reopened.close()

    def test_unknown_effect_cannot_be_settled_without_reconciliation(self):
        self._permitted()
        self.effects.begin_dispatch(
            stream_id="task-1", effect_id="github-issue-1", action_digest="sha256:action-001",
            permit_id="permit-1", dispatcher_id="worker-1",
        )
        self.effects.mark_unknown(
            stream_id="task-1", effect_id="github-issue-1", actor_id="system", reason_code="disconnect",
        )
        with self.assertRaises(EffectTransitionError):
            self.effects.settle(
                stream_id="task-1", effect_id="github-issue-1",
                outcome="succeeded", actor_id="worker",
            )


if __name__ == "__main__":
    unittest.main()
