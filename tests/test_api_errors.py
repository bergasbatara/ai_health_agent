from fastapi.testclient import TestClient

from api import WorkflowExecutionError, create_app
import api.dependencies as deps


def test_workflow_not_found_is_rendered_as_structured_404():
    client = TestClient(create_app())

    response = client.get("/cases/missing-workflow")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workflow_not_found"


def test_workflow_execution_error_is_rendered_as_structured_500():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    original = deps.ApiServices.run_workflow

    def fail_run_workflow(self, request):
        raise WorkflowExecutionError("execution blew up")

    deps.ApiServices.run_workflow = fail_run_workflow
    try:
        response = client.post(
            "/cases",
            json={
                "case_path": "tmp/case-001.json",
                "data_dir": "data",
                "use_mock_crews": True,
                "top_k": 5,
            },
        )
    finally:
        deps.ApiServices.run_workflow = original

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "workflow_execution_failed"
