from datetime import datetime, timedelta, timezone

from orchestration import (
    FailureDisposition,
    RetryPolicy,
    StepExecutionRecord,
    StepStatus,
    WorkflowArtifactBundle,
    WorkflowFailure,
    WorkflowResult,
    WorkflowRunStatus,
    WorkflowState,
    WorkflowStep,
)
from rules_engine import IssueSeverity, ValidationIssue


def make_issue() -> ValidationIssue:
    return ValidationIssue(
        code="missing_field",
        message="A required field is missing.",
        severity=IssueSeverity.ERROR,
        field_path="patient_case.payer_name",
    )


def test_workflow_state_accepts_minimal_valid_payload():
    state = WorkflowState(workflow_id="workflow-001")

    assert state.workflow_id == "workflow-001"
    assert state.status == WorkflowRunStatus.NOT_STARTED
    assert state.current_step is None
    assert state.artifacts == WorkflowArtifactBundle()


def test_workflow_state_requires_current_step_when_running():
    try:
        WorkflowState(
            workflow_id="workflow-001",
            status=WorkflowRunStatus.RUNNING,
        )
    except ValueError as exc:
        assert "current_step must be set" in str(exc)
    else:
        raise AssertionError("Expected ValueError for running workflow without current_step")


def test_step_execution_record_requires_failure_for_failed_status():
    try:
        StepExecutionRecord(
            step=WorkflowStep.POLICY_MATCHING,
            status=StepStatus.FAILED,
            attempts=1,
        )
    except ValueError as exc:
        assert "failure must be provided" in str(exc)
    else:
        raise AssertionError("Expected ValueError for failed step without failure")


def test_step_execution_record_rejects_completion_before_start():
    started_at = datetime.now(timezone.utc)
    completed_at = started_at - timedelta(seconds=1)

    try:
        StepExecutionRecord(
            step=WorkflowStep.POLICY_MATCHING,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            started_at=started_at,
            completed_at=completed_at,
        )
    except ValueError as exc:
        assert "completed_at must be on or after started_at" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid execution timestamps")


def test_workflow_state_rejects_duplicate_step_attempt_pairs():
    record = StepExecutionRecord(
        step=WorkflowStep.CASE_INTAKE,
        status=StepStatus.SUCCEEDED,
        attempts=1,
    )

    try:
        WorkflowState(
            workflow_id="workflow-001",
            step_history=[record, record],
        )
    except ValueError as exc:
        assert "Duplicate step history record" in str(exc)
    else:
        raise AssertionError("Expected ValueError for duplicate step history entries")


def test_workflow_result_preserves_failures_and_issues():
    failure = WorkflowFailure(
        step=WorkflowStep.RULES_VALIDATION,
        disposition=FailureDisposition.HUMAN_REVIEW,
        message="Deterministic validation blocked submission readiness.",
        retry_count=0,
        issues=[make_issue()],
    )
    result = WorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowRunStatus.NEEDS_HUMAN_REVIEW,
        artifacts=WorkflowArtifactBundle(),
        issues=[make_issue()],
        failures=[failure],
        step_history=[],
    )

    assert result.status == WorkflowRunStatus.NEEDS_HUMAN_REVIEW
    assert result.failures[0].disposition == FailureDisposition.HUMAN_REVIEW
    assert result.issues[0].code == "missing_field"


def test_retry_policy_constrains_attempts_and_steps():
    policy = RetryPolicy(
        max_attempts=3,
        retryable_steps=[WorkflowStep.FACT_EXTRACTION, WorkflowStep.POLICY_MATCHING],
        backoff_seconds=2.5,
    )

    assert policy.max_attempts == 3
    assert policy.retryable_steps == [
        WorkflowStep.FACT_EXTRACTION,
        WorkflowStep.POLICY_MATCHING,
    ]
    assert policy.backoff_seconds == 2.5
