from fastapi.testclient import TestClient

from api import create_app
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
            }
        },
        issues=[],
        failures=[],
        step_history=[{"step": "case_intake", "status": "succeeded", "attempts": 1}],
    )


def test_submit_case_runs_workflow_and_persists_result(monkeypatch):
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr("api.routes.cases._execute_workflow", lambda payload: make_workflow_result())

    response = client.post(
        "/cases",
        json={
            "case_path": "tmp/case-001.json",
            "data_dir": "data",
            "use_mock_crews": True,
            "top_k": 5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["workflow"]["workflow_id"] == "workflow-001"
    assert body["workflow"]["case_id"] == "case-001"
    assert app.state.workflow_store.has_workflow("workflow-001") is True


def test_list_cases_returns_saved_case_summaries():
    app = create_app()
    app.state.workflow_store.save_result(make_workflow_result())
    client = TestClient(app)

    response = client.get("/cases")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["workflow_id"] == "workflow-001"


def test_get_case_status_returns_404_for_missing_workflow():
    client = TestClient(create_app())

    response = client.get("/cases/missing-workflow")

    assert response.status_code == 404
    assert "missing-workflow" in response.json()["detail"]
