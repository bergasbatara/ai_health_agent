from __future__ import annotations

from pydantic import ValidationError

from agents.runtime import AgentRuntimeError
from rules_engine import IssueSeverity, RulesEngineServiceResult

from .models import FailureDisposition, RetryPolicy, ValidationIssue, WorkflowFailure, WorkflowRunStatus, WorkflowStep
from .steps import get_step_definition


def classify_workflow_exception(
    step: WorkflowStep,
    error: Exception,
    *,
    retry_count: int = 0,
) -> WorkflowFailure:
    if isinstance(error, AgentRuntimeError):
        disposition = FailureDisposition.RETRYABLE if get_step_definition(step).supports_retry else FailureDisposition.FATAL
    elif isinstance(error, (TimeoutError, ConnectionError)):
        disposition = FailureDisposition.RETRYABLE if get_step_definition(step).supports_retry else FailureDisposition.FATAL
    elif isinstance(error, (FileNotFoundError, IsADirectoryError, NotADirectoryError)):
        disposition = FailureDisposition.FATAL
    elif isinstance(error, ValidationError | ValueError):
        disposition = FailureDisposition.FATAL
    else:
        disposition = FailureDisposition.FATAL

    return WorkflowFailure(
        step=step,
        disposition=disposition,
        message=str(error) or error.__class__.__name__,
        error_type=error.__class__.__name__,
        retry_count=retry_count,
    )


def should_retry_step(
    step: WorkflowStep,
    failure: WorkflowFailure,
    retry_policy: RetryPolicy,
    *,
    attempts_so_far: int,
) -> bool:
    if failure.disposition != FailureDisposition.RETRYABLE:
        return False
    if step not in retry_policy.retryable_steps:
        return False
    if not get_step_definition(step).supports_retry:
        return False
    return attempts_so_far < retry_policy.max_attempts


def should_require_human_review(rules_result: RulesEngineServiceResult) -> bool:
    if not rules_result.passed:
        return True
    return any(issue.severity == IssueSeverity.WARNING for issue in rules_result.issues)


def make_human_review_failure(
    step: WorkflowStep,
    *,
    message: str,
    issues: list[ValidationIssue] | None = None,
) -> WorkflowFailure:
    return WorkflowFailure(
        step=step,
        disposition=FailureDisposition.HUMAN_REVIEW,
        message=message,
        error_type=None,
        retry_count=0,
        issues=list(issues or []),
    )


def resolve_terminal_workflow_status(
    *,
    failures: list[WorkflowFailure],
    rules_result: RulesEngineServiceResult | None = None,
) -> WorkflowRunStatus:
    if any(failure.disposition == FailureDisposition.FATAL for failure in failures):
        return WorkflowRunStatus.FAILED
    if any(failure.disposition == FailureDisposition.HUMAN_REVIEW for failure in failures):
        return WorkflowRunStatus.NEEDS_HUMAN_REVIEW
    if rules_result is not None and should_require_human_review(rules_result):
        return WorkflowRunStatus.NEEDS_HUMAN_REVIEW
    return WorkflowRunStatus.SUCCEEDED
