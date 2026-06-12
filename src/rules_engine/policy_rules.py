from __future__ import annotations

from domain import CriterionStatus, PolicyMatchResult, RecommendationSignal

from .common import evaluate_checks, make_error, make_rule_check
from .models import RuleCheckResult, RulesEvaluationResult


def check_policy_result_has_citations(policy_match_result: PolicyMatchResult) -> RuleCheckResult:
    issues = []
    if not policy_match_result.cited_evidence:
        issues.append(
            make_error(
                "missing_policy_citations",
                "Policy match result must include cited evidence.",
                "policy_match_result.cited_evidence",
            )
        )
    return make_rule_check("check_policy_result_has_citations", issues)


def check_criteria_have_rationale_and_evidence(policy_match_result: PolicyMatchResult) -> RuleCheckResult:
    issues = []
    for index, criterion in enumerate(policy_match_result.criteria):
        field_prefix = f"policy_match_result.criteria[{index}]"
        if criterion.status in {CriterionStatus.MET, CriterionStatus.NOT_MET}:
            if not criterion.rationale.strip():
                issues.append(
                    make_error(
                        "missing_criterion_rationale",
                        f"Criterion '{criterion.criterion_key}' must include rationale.",
                        f"{field_prefix}.rationale",
                    )
                )
            if not criterion.policy_evidence:
                issues.append(
                    make_error(
                        "missing_criterion_evidence",
                        f"Criterion '{criterion.criterion_key}' must include policy evidence.",
                        f"{field_prefix}.policy_evidence",
                    )
                )
    return make_rule_check("check_criteria_have_rationale_and_evidence", issues)


def check_recommendation_signal_consistency(policy_match_result: PolicyMatchResult) -> RuleCheckResult:
    issues = []
    has_not_met_criterion = any(criterion.status == CriterionStatus.NOT_MET for criterion in policy_match_result.criteria)
    if (
        policy_match_result.recommendation_signal == RecommendationSignal.LIKELY_APPROVE
        and has_not_met_criterion
    ):
        issues.append(
            make_error(
                "inconsistent_recommendation_signal",
                "Recommendation signal cannot be likely_approve when at least one criterion is not_met.",
                "policy_match_result.recommendation_signal",
            )
        )
    return make_rule_check("check_recommendation_signal_consistency", issues)


def evaluate_policy_rules(policy_match_result: PolicyMatchResult) -> RulesEvaluationResult:
    checks = [
        check_policy_result_has_citations(policy_match_result),
        check_criteria_have_rationale_and_evidence(policy_match_result),
        check_recommendation_signal_consistency(policy_match_result),
    ]
    return evaluate_checks(checks)
