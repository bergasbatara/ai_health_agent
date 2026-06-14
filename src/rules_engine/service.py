from __future__ import annotations

from domain import ExtractedClinicalFacts, PatientCase, PolicyMatchResult, PriorAuthDraft

from .case_rules import evaluate_case_rules
from .common import collect_issues
from .draft_rules import evaluate_draft_rules
from .models import RuleCheckResult, RulesEngineServiceResult
from .policy_rules import evaluate_policy_rules


def evaluate_prior_auth_package(
    patient_case: PatientCase,
    extracted_facts: ExtractedClinicalFacts,
    policy_match_result: PolicyMatchResult,
    prior_auth_draft: PriorAuthDraft,
) -> RulesEngineServiceResult:
    case_evaluation = evaluate_case_rules(patient_case, extracted_facts)
    policy_evaluation = evaluate_policy_rules(policy_match_result)
    draft_evaluation = evaluate_draft_rules(prior_auth_draft, policy_match_result)

    checks: list[RuleCheckResult] = [
        *case_evaluation.checks,
        *policy_evaluation.checks,
        *draft_evaluation.checks,
    ]
    issues = collect_issues(checks)

    return RulesEngineServiceResult(
        passed=all(
            evaluation.passed
            for evaluation in (
                case_evaluation,
                policy_evaluation,
                draft_evaluation,
            )
        ),
        case_evaluation=case_evaluation,
        policy_evaluation=policy_evaluation,
        draft_evaluation=draft_evaluation,
        checks=checks,
        issues=issues,
    )
