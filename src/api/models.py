from __future__ import annotations

from pydantic import Field, field_validator

from domain import ExtractedClinicalFacts, PolicyMatchResult, PriorAuthDraft
from chat import ChatResponse
from domain.models import DomainModel
from orchestration import WorkflowFailure, WorkflowResult, WorkflowRunStatus
from retrieval import RetrievalResult
from rules_engine import ValidationIssue


class HealthResponse(DomainModel):
    status: str = Field(default="ok", min_length=1)
    service: str = Field(default="ai-health-agent-api", min_length=1)


class SubmitCaseRequest(DomainModel):
    case_path: str = Field(min_length=1)
    workflow_id: str | None = None
    data_dir: str = Field(default="data", min_length=1)
    use_mock_crews: bool = False
    model: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("case_path")
    @classmethod
    def case_path_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("case_path must not be blank")
        return value

    @field_validator("data_dir")
    @classmethod
    def data_dir_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("data_dir must not be blank")
        return value


class CaseSummaryResponse(DomainModel):
    workflow_id: str = Field(min_length=1)
    case_id: str | None = None
    status: WorkflowRunStatus
    current_step: str | None = None
    issue_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    issues: list[ValidationIssue] = Field(default_factory=list)
    failures: list[WorkflowFailure] = Field(default_factory=list)


class SubmitCaseResponse(DomainModel):
    workflow: CaseSummaryResponse
    result: WorkflowResult


class ExtractedFactsResponse(DomainModel):
    workflow_id: str = Field(min_length=1)
    status: WorkflowRunStatus
    extracted_facts: ExtractedClinicalFacts | None = None


class PolicyEvidenceResponse(DomainModel):
    workflow_id: str = Field(min_length=1)
    status: WorkflowRunStatus
    retrieval_result: RetrievalResult | None = None


class PolicyMatchResponse(DomainModel):
    workflow_id: str = Field(min_length=1)
    status: WorkflowRunStatus
    policy_match_result: PolicyMatchResult | None = None


class DraftOutputResponse(DomainModel):
    workflow_id: str = Field(min_length=1)
    status: WorkflowRunStatus
    prior_auth_draft: PriorAuthDraft | None = None


class CaseChatRequest(DomainModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class CaseChatResponse(DomainModel):
    workflow_id: str = Field(min_length=1)
    status: WorkflowRunStatus
    chat_response: ChatResponse


def build_case_summary_response(result: WorkflowResult) -> CaseSummaryResponse:
    last_step = result.step_history[-1].step if result.step_history else None
    case_id = result.artifacts.patient_case.case_id if result.artifacts.patient_case is not None else None
    return CaseSummaryResponse(
        workflow_id=result.workflow_id,
        case_id=case_id,
        status=result.status,
        current_step=last_step,
        issue_count=len(result.issues),
        failure_count=len(result.failures),
        issues=result.issues,
        failures=result.failures,
    )
