from api import InMemoryWorkflowStore, WorkflowResultNotFoundError
from orchestration import WorkflowResult, WorkflowRunStatus


def make_workflow_result(
    *,
    workflow_id: str = "workflow-001",
    case_id: str = "case-001",
) -> WorkflowResult:
    return WorkflowResult(
        workflow_id=workflow_id,
        status=WorkflowRunStatus.SUCCEEDED,
        artifacts={
            "patient_case": {
                "case_id": case_id,
                "payer_id": "aetna",
                "payer_name": "Aetna",
                "requested_modality": "mri",
                "requested_body_region": "knee",
                "requested_laterality": "left",
                "ordering_specialty": "orthopedics",
                "raw_clinical_note": "Knee pain.",
            },
            "extracted_facts": {
                "case_id": case_id,
                "requested_modality": "mri",
                "requested_body_region": "knee",
                "requested_laterality": "left",
                "conservative_therapy_completed": "yes",
                "prior_imaging_completed": "yes",
                "red_flags_present": "unknown",
                "contraindications_present": "unknown",
            },
            "retrieval_result": {
                "query": {"query_text": "knee mri", "top_k": 5},
                "hits": [],
                "evidence": [],
            },
            "policy_match_result": {
                "case_id": case_id,
                "payer_id": "aetna",
                "payer_name": "Aetna",
                "requested_modality": "mri",
                "requested_body_region": "knee",
                "requested_laterality": "left",
                "policy_requirements_summary": "Summary",
                "criteria": [],
                "unresolved_questions": [],
                "cited_evidence": [],
            },
            "prior_auth_draft": {
                "case_id": case_id,
                "review_status": "needs_review",
                "reviewer_summary": "Draft generated.",
                "missing_requirements": [],
                "unresolved_issues": [],
                "risk_flags": [],
            },
        },
    )


def test_store_saves_and_gets_workflow_result():
    store = InMemoryWorkflowStore()
    result = make_workflow_result()

    store.save_result(result)

    assert store.get_result("workflow-001").workflow_id == "workflow-001"
    assert store.has_workflow("workflow-001") is True


def test_store_can_get_result_by_case_id():
    store = InMemoryWorkflowStore()
    result = make_workflow_result(workflow_id="workflow-002", case_id="case-123")
    store.save_result(result)

    fetched = store.get_result_by_case_id("case-123")

    assert fetched.workflow_id == "workflow-002"


def test_store_exposes_artifact_accessors():
    store = InMemoryWorkflowStore()
    store.save_result(make_workflow_result())

    assert store.get_extracted_facts("workflow-001") is not None
    assert store.get_retrieval_result("workflow-001") is not None
    assert store.get_policy_match_result("workflow-001") is not None
    assert store.get_prior_auth_draft("workflow-001") is not None


def test_store_delete_removes_workflow_and_case_index():
    store = InMemoryWorkflowStore()
    store.save_result(make_workflow_result())

    deleted = store.delete_result("workflow-001")

    assert deleted.workflow_id == "workflow-001"
    assert store.has_workflow("workflow-001") is False
    try:
        store.get_result_by_case_id("case-001")
    except WorkflowResultNotFoundError:
        pass
    else:
        raise AssertionError("Expected WorkflowResultNotFoundError after deletion")


def test_store_raises_not_found_for_missing_result():
    store = InMemoryWorkflowStore()

    try:
        store.get_result("missing-workflow")
    except WorkflowResultNotFoundError as exc:
        assert "missing-workflow" in str(exc)
    else:
        raise AssertionError("Expected WorkflowResultNotFoundError for missing workflow")
