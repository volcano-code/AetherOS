import unittest

from aetheros.tasks.models import Task, TaskState, transition
from aetheros.harness.schema import HarnessSpec
from aetheros.security.approval import ApprovalRequest, ApprovalStatus, decide
from aetheros.rsi.gates import Evaluation, PromotionDecision, evaluate_promotion


class TaskStateTests(unittest.TestCase):
    def test_valid_transition(self):
        task = Task("t1", "u1", "prepare report")
        self.assertEqual(transition(task, TaskState.PLANNED).state, TaskState.PLANNED)

    def test_invalid_terminal_transition(self):
        task = Task("t1", "u1", "prepare report", state=TaskState.COMPLETED)
        with self.assertRaises(ValueError):
            transition(task, TaskState.RUNNING)


class HarnessTests(unittest.TestCase):
    def test_digest_is_deterministic(self):
        a = HarnessSpec("research", "cite sources", tool_policy={"web": True})
        b = HarnessSpec("research", "cite sources", tool_policy={"web": True})
        self.assertEqual(a.digest, b.digest)

    def test_digest_changes_when_spec_changes(self):
        a = HarnessSpec("research", "cite sources")
        b = HarnessSpec("research", "do not cite sources")
        self.assertNotEqual(a.digest, b.digest)


class ApprovalTests(unittest.TestCase):
    def test_approval_is_bound_to_action_digest(self):
        request = ApprovalRequest("r1", "u1", "sha256:abc")
        with self.assertRaises(ValueError):
            decide(request, actor_id="u1", action_digest="sha256:other", approve=True)

    def test_approved_request_records_actor(self):
        request = ApprovalRequest("r1", "u1", "sha256:abc")
        result = decide(request, actor_id="u1", action_digest="sha256:abc", approve=True)
        self.assertEqual(result.status, ApprovalStatus.APPROVED)
        self.assertEqual(result.decided_by, "u1")


class RsiGateTests(unittest.TestCase):
    def test_rejects_safety_regression(self):
        result = Evaluation(.60, .70, 0, 1, .60, .60, 50)
        self.assertEqual(evaluate_promotion(result), PromotionDecision.REJECT)

    def test_requires_independent_sample(self):
        result = Evaluation(.60, .70, 0, 0, .60, .60, 10)
        self.assertEqual(evaluate_promotion(result), PromotionDecision.INSUFFICIENT_EVIDENCE)

    def test_promotes_only_when_all_gates_pass(self):
        result = Evaluation(.60, .66, 0, 0, .60, .59, 50)
        self.assertEqual(evaluate_promotion(result), PromotionDecision.PROMOTE)


if __name__ == "__main__":
    unittest.main()
