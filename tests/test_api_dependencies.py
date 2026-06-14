from api import ApiServices, InMemoryWorkflowStore
from api.models import SubmitCaseRequest
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
            }
        },
    )


def test_api_services_run_workflow_persists_result(monkeypatch):
    store = InMemoryWorkflowStore()
    services = ApiServices(workflow_store=store)

    monkeypatch.setattr("api.dependencies.build_searcher_from_data_dir", lambda data_dir: "fake-searcher")
    monkeypatch.setattr("api.dependencies.build_mock_crews", lambda: ("extractor", "policy", "draft"))
    monkeypatch.setattr("api.dependencies.run_prior_auth_workflow_with_crewai", lambda **kwargs: make_workflow_result())

    result = services.run_workflow(
        SubmitCaseRequest(
            case_path="tmp/case-001.json",
            data_dir="data",
            use_mock_crews=True,
            workflow_id="workflow-001",
        )
    )

    assert result.workflow_id == "workflow-001"
    assert store.has_workflow("workflow-001") is True
