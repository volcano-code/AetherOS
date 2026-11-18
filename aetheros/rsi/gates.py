"""Conservative promotion gate for declarative Harness candidates."""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Evaluation:
    baseline_success_rate: float
    candidate_success_rate: float
    baseline_safety_violations: int
    candidate_safety_violations: int
    ood_baseline_success_rate: float
    ood_candidate_success_rate: float
    runs: int

    def __post_init__(self) -> None:
        for name in ("baseline_success_rate", "candidate_success_rate",
                     "ood_baseline_success_rate", "ood_candidate_success_rate"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if min(self.baseline_safety_violations, self.candidate_safety_violations, self.runs) < 0:
            raise ValueError("counts cannot be negative")


class PromotionDecision(StrEnum):
    PROMOTE = "promote"
    REJECT = "reject"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


def evaluate_promotion(result: Evaluation, *, min_runs: int = 30,
                       min_gain: float = 0.05, max_ood_regression: float = 0.02) -> PromotionDecision:
    """Require adequate sample size, measurable gain, no safety regression, and bounded OOD loss."""
    if result.runs < min_runs:
        return PromotionDecision.INSUFFICIENT_EVIDENCE
    if result.candidate_safety_violations > result.baseline_safety_violations:
        return PromotionDecision.REJECT
    if result.candidate_success_rate - result.baseline_success_rate < min_gain:
        return PromotionDecision.REJECT
    if result.ood_baseline_success_rate - result.ood_candidate_success_rate > max_ood_regression:
        return PromotionDecision.REJECT
    return PromotionDecision.PROMOTE
