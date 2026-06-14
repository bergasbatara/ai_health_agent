from agents.runtime import AgentRuntimeError
from domain import BodyRegion, CoverageCriterion, CriterionStatus, ImagingModality, PolicyEvidence, PolicyMatchResult, PayerId
from orchestration import (
    FailureDisposition,
    RetryPolicy,
    WorkflowRunStatus,
    WorkflowStep,
    classify_workflow_exception,
    make_human_review_failure,
    resolve_terminal_workflow_status,
    should_require_human_review,
    should_retry_step,
)
from rules_engine import IssueSeverity, RulesEngineServiceResult, RulesEvaluationResult, ValidationIssue


def make_issue(*, severity: IssueSeverity) -> ValidationIssue:
    return ValidationIssue(
        code="test_issue",
        message="Test issue.",
        severity=severity,
        field_path="field.path",
    )


def make_rules_result(*, passed: bool, issues: list[ValidationIssue]) -> RulesEngineServiceResult:
    evaluation = RulesEvaluationResult(passed=passed, checks=[], issues=issues)
    return RulesEngineServiceResult(
        passed=passed,
        case_evaluation=evaluation,
        policy_evaluation=evaluation,
        draft_evaluation=evaluation,
        checks=[],
        issues=issues,
    )


def test_classify_workflow_exception_marks_agent_errors_retryable_for_retryable_step():
    failure = classify_workflow_exception(
        WorkflowStep.FACT_EXTRACTION,
        AgentRuntimeError("bad llm response"),
        retry_count=1,
    )

    assert failure.disposition == FailureDisposition.RETRYABLE
    assert failure.error_type == "AgentRuntimeError"
    assert failure.retry_count == 1


def test_classify_workflow_exception_marks_filesystem_errors_fatal():
    failure = classify_workflow_exception(
        WorkflowStep.CASE_INTAKE,
        FileNotFoundError("missing case"),
    )

    assert failure.disposition == FailureDisposition.FATAL


def test_should_retry_step_requires_retryable_failure_and_policy_support():
    policy = RetryPolicy(
        max_attempts=3,
        retryable_steps=[WorkflowStep.FACT_EXTRACTION, WorkflowStep.POLICY_MATCHING],
    )
    failure = classify_workflow_exception(
        WorkflowStep.FACT_EXTRACTION,
        AgentRuntimeError("bad llm response"),
    )

    assert should_retry_step(
        WorkflowStep.FACT_EXTRACTION,
        failure,
        policy,
        attempts_so_far=1,
    ) is True
    assert should_retry_step(
        WorkflowStep.FACT_EXTRACTION,
        failure,
        policy,
        attempts_so_far=3,
    ) is False


def test_should_require_human_review_for_failed_rules_result():
    rules_result = make_rules_result(
        passed=False,
        issues=[make_issue(severity=IssueSeverity.ERROR)],
    )

    assert should_require_human_review(rules_result) is True


def test_should_require_human_review_for_warning_only_rules_result():
    rules_result = make_rules_result(
        passed=True,
        issues=[make_issue(severity=IssueSeverity.WARNING)],
    )

    assert should_require_human_review(rules_result) is True


def test_resolve_terminal_workflow_status_prefers_fatal_failures():
    fatal_failure = classify_workflow_exception(
        WorkflowStep.CASE_INTAKE,
        ValueError("bad payload"),
    )
    human_review_failure = make_human_review_failure(
        WorkflowStep.RULES_VALIDATION,
        message="Needs reviewer attention.",
    )

    status = resolve_terminal_workflow_status(
        failures=[fatal_failure, human_review_failure],
        rules_result=None,
    )

    assert status == WorkflowRunStatus.FAILED


def test_resolve_terminal_workflow_status_returns_human_review_for_rules_gate():
    rules_result = make_rules_result(
        passed=True,
        issues=[make_issue(severity=IssueSeverity.WARNING)],
    )

    status = resolve_terminal_workflow_status(
        failures=[],
        rules_result=rules_result,
    )

    assert status == WorkflowRunStatus.NEEDS_HUMAN_REVIEW


def test_resolve_terminal_workflow_status_returns_success_when_no_blockers():
    rules_result = make_rules_result(
        passed=True,
        issues=[],
    )

    status = resolve_terminal_workflow_status(
        failures=[],
        rules_result=rules_result,
    )

    assert status == WorkflowRunStatus.SUCCEEDED
