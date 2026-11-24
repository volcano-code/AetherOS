import unittest
from dataclasses import replace

from aetheros.capabilities import (
    CapabilityAdmissionError, CapabilityManifest, CapabilityRegistry,
)
from aetheros.rsi import (
    PlaybookCandidate, PlaybookEvaluation, PromotionDecision, SessionLearning,
    evaluate_playbook, promote_playbook,
)


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.registry = CapabilityRegistry()
        self.v1 = CapabilityManifest(
            "github-connector", "1.0.0", network_hosts=("api.github.com",),
            filesystem_read=("workspace/reports/*",),
        )

    def test_unreviewed_manifest_cannot_be_pinned(self):
        with self.assertRaises(CapabilityAdmissionError):
            self.registry.pin("session-1", self.v1)

    def test_trust_is_bound_to_exact_manifest_digest(self):
        self.registry.review(self.v1, reviewer_id="admin", approve=True)
        pin = self.registry.pin("session-1", self.v1)
        self.assertEqual(pin.manifest_digest, self.v1.digest)
        v2 = CapabilityManifest(
            "github-connector", "2.0.0",
            network_hosts=("api.github.com", "evil.example"),
        )
        with self.assertRaises(CapabilityAdmissionError):
            self.registry.pin("session-1", v2)

    def test_session_pin_requires_explicit_migration(self):
        self.registry.review(self.v1, reviewer_id="admin", approve=True)
        self.registry.pin("session-1", self.v1)
        v2 = CapabilityManifest("github-connector", "2.0.0", network_hosts=("api.github.com",))
        self.registry.review(v2, reviewer_id="admin", approve=True)
        with self.assertRaises(CapabilityAdmissionError):
            self.registry.pin("session-1", v2)
        migrated = self.registry.migrate_pin("session-1", v2, approved_by="admin")
        self.assertEqual(migrated.version, "2.0.0")


class PlaybookTests(unittest.TestCase):
    def setUp(self):
        self.candidate = PlaybookCandidate(
            candidate_id="research-cite-v2", name="Research Citation Playbook", version="2.0.0",
            rule="Verify every factual claim against a source before finalizing.",
            source_session_ids=("s1", "s2", "s3", "s4", "s5"),
            evidence_digests=("sha256:e1", "sha256:e2"),
        )
        self.good = PlaybookEvaluation(
            baseline_success_rate=0.60, candidate_success_rate=0.68,
            ood_baseline_success_rate=0.60, ood_candidate_success_rate=0.59,
            baseline_safety_violations=0, candidate_safety_violations=0,
            runs=50, distinct_tasks=20, source_sessions=5,
            candidate_digest=self.candidate.digest, baseline_harness_digest="sha256:baseline",
            benchmark_digest="sha256:benchmark", ood_dataset_digest="sha256:ood",
            model_route="approved-model", budget_profile="standard-v1",
        )

    def test_session_learning_is_scoped_to_one_session(self):
        lesson = SessionLearning("l1", "s1", "research", "include source URLs", "sha256:e1")
        self.assertEqual(lesson.session_id, "s1")
        self.assertFalse(hasattr(lesson, "promote"))

    def test_insufficient_cross_task_evidence_blocks_promotion(self):
        weak = replace(self.good, source_sessions=2)
        self.assertEqual(evaluate_playbook(weak), PromotionDecision.INSUFFICIENT_EVIDENCE)

    def test_safety_or_ood_regression_blocks_promotion(self):
        unsafe = replace(self.good, candidate_safety_violations=1)
        self.assertEqual(evaluate_playbook(unsafe), PromotionDecision.REJECT)
        ood_bad = replace(self.good, ood_candidate_success_rate=0.50)
        self.assertEqual(evaluate_playbook(ood_bad), PromotionDecision.REJECT)

    def test_global_playbook_promotion_requires_human_approval(self):
        with self.assertRaises(PermissionError):
            promote_playbook(self.candidate, self.good, reviewer_id="admin", human_approved=False)
        release = promote_playbook(
            self.candidate, self.good, reviewer_id="admin", human_approved=True,
        )
        self.assertEqual(release.candidate_digest, self.candidate.digest)
        self.assertEqual(release.approved_by, "admin")
        self.assertEqual(release.benchmark_digest, "sha256:benchmark")

    def test_evaluation_must_be_bound_to_candidate_digest(self):
        bad = replace(self.good, candidate_digest="sha256:other")
        with self.assertRaises(ValueError):
            promote_playbook(self.candidate, bad, reviewer_id="admin", human_approved=True)

    def test_candidate_requires_multiple_source_sessions(self):
        with self.assertRaises(ValueError):
            PlaybookCandidate("x", "x", "1", "rule", ("s1",), ("sha256:e1",))


if __name__ == "__main__":
    unittest.main()
