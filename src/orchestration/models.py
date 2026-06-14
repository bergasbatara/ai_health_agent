from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from agents.models import ExtractorOutput, FormFillerOutput, PolicyMatcherOutput
from case_intake.models import RawCaseFile
from domain import ExtractedClinicalFacts, PatientCase, PolicyMatchResult, PriorAuthDraft
from domain.models import DomainModel
from retrieval.models import RetrievalResult
from rules_engine.models import RulesEngineServiceResult, ValidationIssue


class WorkflowStep(StrEnum):
    CASE_INTAKE = "case_intake"
    FACT_EXTRACTION = "fact_extraction"
    POLICY_RETRIEVAL = "policy_retrieval"
    POLICY_MATCHING = "policy_matching"
    DRAFT_GENERATION = "draft_generation"
    RULES_VALIDATION = "rules_validation"


class StepStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowRunStatus(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class FailureDisposition(StrEnum):
    RETRYABLE = "retryable"
    FATAL = "fatal"
    HUMAN_REVIEW = "human_review"


class RetryPolicy(DomainModel):
    max_attempts: int = Field(default=2, ge=1, le=10)
    retryable_steps: list[WorkflowStep] = Field(default_factory=list)
    backoff_seconds: float = Field(default=0.0, ge=0.0, le=300.0)


class WorkflowFailure(DomainModel):
    step: WorkflowStep
    disposition: FailureDisposition
    message: str = Field(min_length=1)
    error_type: str | None = None
    retry_count: int = Field(default=0, ge=0)
    issues: list[ValidationIssue] = Field(default_factory=list)


class StepExecutionRecord(DomainModel):
    step: WorkflowStep
    status: StepStatus = StepStatus.NOT_STARTED
    attempts: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure: WorkflowFailure | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_completion_fields(self) -> "StepExecutionRecord":
        if self.status == StepStatus.FAILED and self.failure is None:
            raise ValueError("failure must be provided when step status is failed")
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValueError("completed_at must be on or after started_at")
        return self


class WorkflowArtifactBundle(DomainModel):
    raw_case_file: RawCaseFile | None = None
    patient_case: PatientCase | None = None
    extractor_output: ExtractorOutput | None = None
    extracted_facts: ExtractedClinicalFacts | None = None
    retrieval_result: RetrievalResult | None = None
    policy_matcher_output: PolicyMatcherOutput | None = None
    policy_match_result: PolicyMatchResult | None = None
    form_filler_output: FormFillerOutput | None = None
    prior_auth_draft: PriorAuthDraft | None = None
    rules_result: RulesEngineServiceResult | None = None


class WorkflowState(DomainModel):
    workflow_id: str = Field(min_length=1)
    status: WorkflowRunStatus = WorkflowRunStatus.NOT_STARTED
    current_step: WorkflowStep | None = None
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    artifacts: WorkflowArtifactBundle = Field(default_factory=WorkflowArtifactBundle)
    step_history: list[StepExecutionRecord] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    failures: list[WorkflowFailure] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("step_history")
    @classmethod
    def step_history_must_not_repeat_same_attemptless_step(
        cls,
        value: list[StepExecutionRecord],
    ) -> list[StepExecutionRecord]:
        seen: set[tuple[WorkflowStep, int]] = set()
        for record in value:
            key = (record.step, record.attempts)
            if key in seen:
                raise ValueError(f"Duplicate step history record for {record.step} attempt {record.attempts}")
            seen.add(key)
        return value

    @model_validator(mode="after")
    def validate_current_step_alignment(self) -> "WorkflowState":
        if self.status == WorkflowRunStatus.RUNNING and self.current_step is None:
            raise ValueError("current_step must be set when workflow status is running")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must be on or after created_at")
        return self


class WorkflowResult(DomainModel):
    workflow_id: str = Field(min_length=1)
    status: WorkflowRunStatus
    artifacts: WorkflowArtifactBundle
    issues: list[ValidationIssue] = Field(default_factory=list)
    failures: list[WorkflowFailure] = Field(default_factory=list)
    step_history: list[StepExecutionRecord] = Field(default_factory=list)

