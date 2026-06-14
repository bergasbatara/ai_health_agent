from orchestration import (
    WORKFLOW_STEP_DEFINITIONS,
    WORKFLOW_STEP_ORDER,
    WorkflowStep,
    WorkflowStepDefinition,
    get_next_step,
    get_previous_step,
    get_step_definition,
    list_workflow_steps,
)


def test_workflow_step_order_matches_expected_sequence():
    assert WORKFLOW_STEP_ORDER == (
        WorkflowStep.CASE_INTAKE,
        WorkflowStep.FACT_EXTRACTION,
        WorkflowStep.POLICY_RETRIEVAL,
        WorkflowStep.POLICY_MATCHING,
        WorkflowStep.DRAFT_GENERATION,
        WorkflowStep.RULES_VALIDATION,
    )


def test_each_workflow_step_has_definition():
    steps_with_definitions = {definition.step for definition in WORKFLOW_STEP_DEFINITIONS}

    assert steps_with_definitions == set(WORKFLOW_STEP_ORDER)


def test_get_step_definition_returns_expected_metadata():
    definition = get_step_definition(WorkflowStep.POLICY_MATCHING)

    assert isinstance(definition, WorkflowStepDefinition)
    assert definition.depends_on == [WorkflowStep.POLICY_RETRIEVAL]
    assert definition.produces_artifacts == ["policy_matcher_output", "policy_match_result"]
    assert definition.supports_retry is True


def test_navigation_helpers_return_adjacent_steps():
    assert get_previous_step(WorkflowStep.CASE_INTAKE) is None
    assert get_next_step(WorkflowStep.CASE_INTAKE) == WorkflowStep.FACT_EXTRACTION
    assert get_previous_step(WorkflowStep.RULES_VALIDATION) == WorkflowStep.DRAFT_GENERATION
    assert get_next_step(WorkflowStep.RULES_VALIDATION) is None


def test_list_workflow_steps_returns_canonical_order():
    assert list_workflow_steps() == WORKFLOW_STEP_ORDER
