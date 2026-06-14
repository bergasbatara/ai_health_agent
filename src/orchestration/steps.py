from __future__ import annotations

from pydantic import Field, model_validator

from domain.models import DomainModel

from .models import WorkflowStep


class WorkflowStepDefinition(DomainModel):
    step: WorkflowStep
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    depends_on: list[WorkflowStep] = Field(default_factory=list)
    produces_artifacts: list[str] = Field(default_factory=list)
    supports_retry: bool = False

    @model_validator(mode="after")
    def validate_dependencies(self) -> "WorkflowStepDefinition":
        if self.step in self.depends_on:
            raise ValueError("step cannot depend on itself")
        return self


WORKFLOW_STEP_DEFINITIONS: tuple[WorkflowStepDefinition, ...] = (
    WorkflowStepDefinition(
        step=WorkflowStep.CASE_INTAKE,
        display_name="Case Intake",
        description="Load and normalize the input case into the canonical patient-case model.",
        depends_on=[],
        produces_artifacts=["raw_case_file", "patient_case"],
        supports_retry=False,
    ),
    WorkflowStepDefinition(
        step=WorkflowStep.FACT_EXTRACTION,
        display_name="Fact Extraction",
        description="Run the extractor agent and produce normalized clinical facts.",
        depends_on=[WorkflowStep.CASE_INTAKE],
        produces_artifacts=["extractor_output", "extracted_facts"],
        supports_retry=True,
    ),
    WorkflowStepDefinition(
        step=WorkflowStep.POLICY_RETRIEVAL,
        display_name="Policy Retrieval",
        description="Retrieve relevant policy evidence for the requested study and payer.",
        depends_on=[WorkflowStep.FACT_EXTRACTION],
        produces_artifacts=["retrieval_result"],
        supports_retry=True,
    ),
    WorkflowStepDefinition(
        step=WorkflowStep.POLICY_MATCHING,
        display_name="Policy Matching",
        description="Run the policy-matcher agent against patient facts and retrieved evidence.",
        depends_on=[WorkflowStep.POLICY_RETRIEVAL],
        produces_artifacts=["policy_matcher_output", "policy_match_result"],
        supports_retry=True,
    ),
    WorkflowStepDefinition(
        step=WorkflowStep.DRAFT_GENERATION,
        display_name="Draft Generation",
        description="Run the form-filler agent to generate a draft prior-authorization package.",
        depends_on=[WorkflowStep.POLICY_MATCHING],
        produces_artifacts=["form_filler_output", "prior_auth_draft"],
        supports_retry=True,
    ),
    WorkflowStepDefinition(
        step=WorkflowStep.RULES_VALIDATION,
        display_name="Rules Validation",
        description="Apply deterministic checks to the case, policy match, and draft output.",
        depends_on=[WorkflowStep.DRAFT_GENERATION],
        produces_artifacts=["rules_result"],
        supports_retry=False,
    ),
)


STEP_DEFINITION_BY_STEP: dict[WorkflowStep, WorkflowStepDefinition] = {
    definition.step: definition for definition in WORKFLOW_STEP_DEFINITIONS
}

WORKFLOW_STEP_ORDER: tuple[WorkflowStep, ...] = tuple(
    definition.step for definition in WORKFLOW_STEP_DEFINITIONS
)


def get_step_definition(step: WorkflowStep) -> WorkflowStepDefinition:
    return STEP_DEFINITION_BY_STEP[step]


def list_workflow_steps() -> tuple[WorkflowStep, ...]:
    return WORKFLOW_STEP_ORDER


def get_next_step(step: WorkflowStep) -> WorkflowStep | None:
    try:
        index = WORKFLOW_STEP_ORDER.index(step)
    except ValueError as exc:
        raise KeyError(f"Unknown workflow step: {step}") from exc
    if index + 1 >= len(WORKFLOW_STEP_ORDER):
        return None
    return WORKFLOW_STEP_ORDER[index + 1]


def get_previous_step(step: WorkflowStep) -> WorkflowStep | None:
    try:
        index = WORKFLOW_STEP_ORDER.index(step)
    except ValueError as exc:
        raise KeyError(f"Unknown workflow step: {step}") from exc
    if index == 0:
        return None
    return WORKFLOW_STEP_ORDER[index - 1]
