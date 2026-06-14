from fastapi.testclient import TestClient

from api import create_app
from orchestration import WorkflowResult, WorkflowRunStatus


def make_workflow_result() -> WorkflowResult:
    return WorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowRunStatus.SUCCEEDED,
        artifacts={
            "patient_case": {
                "case_id": "case-001",
                "payer_id": "aetna",
                "payer_name": "Aetna",
                "requested_modality": "mri",
                "requested_body_region": "knee",
                "requested_laterality": "left",
                "ordering_specialty": "orthopedics",
                "raw_clinical_note": "Knee pain.",
            },
            "extracted_facts": {
                "case_id": "case-001",
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
                "case_id": "case-001",
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
                "case_id": "case-001",
                "review_status": "needs_review",
                "reviewer_summary": "Draft generated.",
                "missing_requirements": [],
                "unresolved_issues": [],
                "risk_flags": [],
            },
        },
    )


def test_artifact_routes_return_stored_artifacts():
    app = create_app()
    app.state.workflow_store.save_result(make_workflow_result())
    client = TestClient(app)

    facts = client.get("/cases/workflow-001/facts")
    evidence = client.get("/cases/workflow-001/evidence")
    policy_match = client.get("/cases/workflow-001/policy-match")
    draft = client.get("/cases/workflow-001/draft")

    assert facts.status_code == 200
    assert facts.json()["extracted_facts"]["case_id"] == "case-001"
    assert evidence.status_code == 200
    assert evidence.json()["retrieval_result"]["query"]["query_text"] == "knee mri"
    assert policy_match.status_code == 200
    assert policy_match.json()["policy_match_result"]["case_id"] == "case-001"
    assert draft.status_code == 200
    assert draft.json()["prior_auth_draft"]["review_status"] == "needs_review"


def test_artifact_routes_return_404_for_missing_workflow():
    client = TestClient(create_app())

    response = client.get("/cases/missing-workflow/facts")

    assert response.status_code == 404
    assert "missing-workflow" in response.json()["detail"]
