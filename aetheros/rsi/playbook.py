"""Two-level RSI: session-local learning and reviewed cross-task Playbooks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .gates import PromotionDecision
from aetheros.security.approval import ApprovalRequest, ApprovalStatus


@dataclass(frozen=True, slots=True)
class SessionLearning:
    """A local lesson tied to one session; it is never a global Harness release."""

    entry_id: str
    session_id: str
    category: str
    observation: str
    evidence_digest: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (
            self.entry_id, self.session_id, self.category, self.observation, self.evidence_digest
        )):
            raise ValueError("session learning fields must be non-empty")


@dataclass(frozen=True, slots=True)
class PlaybookCandidate:
    """Declarative text/rules only; candidate content is never executable code."""

    candidate_id: str
    name: str
    version: str
    rule: str
    source_session_ids: tuple[str, ...]
    evidence_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.candidate_id, self.name, self.version, self.rule)):
            raise ValueError("candidate fields must be non-empty")
        if any(not value.strip() for value in self.source_session_ids):
            raise ValueError("source session IDs must be non-empty")
        if len(set(self.source_session_ids)) < 2:
            raise ValueError("cross-task Playbook candidates require at least two distinct sessions")
        if not self.evidence_digests or any(not value.strip() for value in self.evidence_digests):
            raise ValueError("Playbook candidate requires non-empty evidence digests")

    @property
    def digest(self) -> str:
        body = {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "version": self.version,
            "rule": self.rule,
            "source_session_ids": sorted(set(self.source_session_ids)),
            "evidence_digests": sorted(set(self.evidence_digests)),
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PlaybookEvaluation:
    baseline_success_rate: float
    candidate_success_rate: float
    ood_baseline_success_rate: float
    ood_candidate_success_rate: float
    baseline_safety_violations: int
    candidate_safety_violations: int
    runs: int
    distinct_tasks: int
    source_sessions: int
    candidate_digest: str
    baseline_harness_digest: str
    benchmark_digest: str
    ood_dataset_digest: str
    model_route: str
    budget_profile: str

    def __post_init__(self) -> None:
        for field_name in (
            "baseline_success_rate", "candidate_success_rate",
            "ood_baseline_success_rate", "ood_candidate_success_rate",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if min(self.baseline_safety_violations, self.candidate_safety_violations,
               self.runs, self.distinct_tasks, self.source_sessions) < 0:
            raise ValueError("evaluation counts cannot be negative")
        for field_name in ("candidate_digest", "baseline_harness_digest", "benchmark_digest",
                           "ood_dataset_digest", "model_route", "budget_profile"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be non-empty for reproducible evaluation")


def evaluate_playbook(
    result: PlaybookEvaluation,
    *,
    min_runs: int = 30,
    min_distinct_tasks: int = 10,
    min_source_sessions: int = 5,
    min_gain: float = 0.05,
    max_ood_regression: float = 0.02,
) -> PromotionDecision:
    """Conservative evidence gate; a PROMOTE result still requires human approval."""
    if min_runs < 1 or min_distinct_tasks < 1 or min_source_sessions < 1:
        raise ValueError("minimum evidence thresholds must be positive")
    if not 0.0 <= min_gain <= 1.0 or not 0.0 <= max_ood_regression <= 1.0:
        raise ValueError("promotion thresholds must be between 0 and 1")
    if min(result.runs, result.distinct_tasks, result.source_sessions) < 0:
        raise ValueError("evaluation counts cannot be negative")
    if (result.runs < min_runs or result.distinct_tasks < min_distinct_tasks
            or result.source_sessions < min_source_sessions):
        return PromotionDecision.INSUFFICIENT_EVIDENCE
    if result.candidate_safety_violations > result.baseline_safety_violations:
        return PromotionDecision.REJECT
    if result.candidate_success_rate - result.baseline_success_rate < min_gain:
        return PromotionDecision.REJECT
    if result.ood_baseline_success_rate - result.ood_candidate_success_rate > max_ood_regression:
        return PromotionDecision.REJECT
    return PromotionDecision.PROMOTE


def playbook_evaluation_digest(evaluation: PlaybookEvaluation) -> str:
    evaluation_body = {
        "candidate_digest": evaluation.candidate_digest,
        "baseline_harness_digest": evaluation.baseline_harness_digest,
        "benchmark_digest": evaluation.benchmark_digest,
        "ood_dataset_digest": evaluation.ood_dataset_digest,
        "model_route": evaluation.model_route,
        "budget_profile": evaluation.budget_profile,
        "runs": evaluation.runs,
        "distinct_tasks": evaluation.distinct_tasks,
        "source_sessions": evaluation.source_sessions,
        "baseline_success_rate": evaluation.baseline_success_rate,
        "candidate_success_rate": evaluation.candidate_success_rate,
        "ood_baseline_success_rate": evaluation.ood_baseline_success_rate,
        "ood_candidate_success_rate": evaluation.ood_candidate_success_rate,
        "baseline_safety_violations": evaluation.baseline_safety_violations,
        "candidate_safety_violations": evaluation.candidate_safety_violations,
    }
    encoded = json.dumps(evaluation_body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def playbook_promotion_digest(candidate: PlaybookCandidate, evaluation: PlaybookEvaluation) -> str:
    if evaluation.candidate_digest != candidate.digest:
        raise ValueError("evaluation is not bound to this exact Playbook candidate digest")
    payload = {"candidate_digest": candidate.digest, "evaluation_digest": playbook_evaluation_digest(evaluation)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PlaybookRelease:
    candidate_digest: str
    version: str
    approved_by: str
    decision: PromotionDecision
    evaluation_digest: str
    benchmark_digest: str
    ood_dataset_digest: str
    model_route: str
    budget_profile: str


def promote_playbook(
    candidate: PlaybookCandidate,
    evaluation: PlaybookEvaluation,
    *,
    approval: ApprovalRequest,
) -> PlaybookRelease:
    if evaluation.candidate_digest != candidate.digest:
        raise ValueError("evaluation is not bound to this exact Playbook candidate digest")
    if evaluation.source_sessions < len(set(candidate.source_session_ids)):
        raise ValueError("evaluation source-session count is smaller than candidate provenance")
    decision = evaluate_playbook(evaluation)
    if decision is not PromotionDecision.PROMOTE:
        raise ValueError(f"candidate did not pass promotion gates: {decision}")
    expected_approval_digest = playbook_promotion_digest(candidate, evaluation)
    if approval.status is not ApprovalStatus.APPROVED or approval.action_digest != expected_approval_digest:
        raise PermissionError("global Playbook promotion requires approval bound to this candidate and evaluation")
    if not approval.decided_by:
        raise PermissionError("Playbook promotion approval is missing a decision actor")
    evaluation_digest = playbook_evaluation_digest(evaluation)
    return PlaybookRelease(
        candidate.digest, candidate.version, approval.decided_by, decision, evaluation_digest,
        evaluation.benchmark_digest, evaluation.ood_dataset_digest, evaluation.model_route,
        evaluation.budget_profile,
    )
