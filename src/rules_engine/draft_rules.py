from __future__ import annotations

from domain import CriterionStatus, PolicyMatchResult, PriorAuthDraft, ReviewStatus

from .common import evaluate_checks, make_error, make_rule_check, make_warning
from .models import RuleCheckResult, RulesEvaluationResult


def check_draft_has_review_status(prior_auth_draft: PriorAuthDraft) -> RuleCheckResult:
    issues = []
    if not str(prior_auth_draft.review_status).strip():
        issues.append(
            make_error(
                "missing_review_status",
                "Prior authorization draft must include a review status.",
                "prior_auth_draft.review_status",
            )
        )
    return make_rule_check("check_draft_has_review_status", issues)


def check_draft_unresolved_issues_consistency(
    prior_auth_draft: PriorAuthDraft,
    policy_match_result: PolicyMatchResult,
) -> RuleCheckResult:
    issues = []
    has_unknown_criteria = any(criterion.status == CriterionStatus.UNKNOWN for criterion in policy_match_result.criteria)
    if (has_unknown_criteria or policy_match_result.unresolved_questions) and not prior_auth_draft.unresolved_issues:
        issues.append(
            make_warning(
                "missing_unresolved_issues",
                "Draft should surface unresolved issues when policy criteria or questions remain unknown.",
                "prior_auth_draft.unresolved_issues",
            )
        )
    return make_rule_check("check_draft_unresolved_issues_consistency", issues)


def check_draft_missing_requirements_consistency(
    prior_auth_draft: PriorAuthDraft,
    policy_match_result: PolicyMatchResult,
) -> RuleCheckResult:
    issues = []
    has_not_met_criteria = any(criterion.status == CriterionStatus.NOT_MET for criterion in policy_match_result.criteria)
    if has_not_met_criteria and not prior_auth_draft.missing_requirements:
        issues.append(
            make_warning(
                "missing_draft_requirements",
                "Draft should list missing requirements when policy criteria are not met.",
                "prior_auth_draft.missing_requirements",
            )
        )
    return make_rule_check("check_draft_missing_requirements_consistency", issues)


def check_draft_review_state_consistency(
    prior_auth_draft: PriorAuthDraft,
    policy_match_result: PolicyMatchResult,
) -> RuleCheckResult:
    issues = []
    has_blockers = any(criterion.status == CriterionStatus.NOT_MET for criterion in policy_match_result.criteria)
    has_open_questions = bool(policy_match_result.unresolved_questions or prior_auth_draft.unresolved_issues)
    if prior_auth_draft.review_status == ReviewStatus.READY_FOR_SUBMISSION and (has_blockers or has_open_questions):
        issues.append(
            make_error(
                "draft_marked_ready_with_blockers",
                "Draft cannot be ready_for_submission while blockers or unresolved issues remain.",
                "prior_auth_draft.review_status",
            )
        )
    return make_rule_check("check_draft_review_state_consistency", issues)


def evaluate_draft_rules(
    prior_auth_draft: PriorAuthDraft,
    policy_match_result: PolicyMatchResult,
) -> RulesEvaluationResult:
    checks = [
        check_draft_has_review_status(prior_auth_draft),
        check_draft_unresolved_issues_consistency(prior_auth_draft, policy_match_result),
        check_draft_missing_requirements_consistency(prior_auth_draft, policy_match_result),
        check_draft_review_state_consistency(prior_auth_draft, policy_match_result),
    ]
    return evaluate_checks(checks)
