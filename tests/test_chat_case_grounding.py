from chat.service import ChatService, ChatServiceConfig
from orchestration import WorkflowResult, WorkflowRunStatus
from tests.test_orchestration_models import make_artifact_bundle


def test_build_case_grounded_request_includes_workflow_artifacts():
    service = ChatService(ChatServiceConfig(siliconflow_api_key="secret"))
    result = WorkflowResult(
        workflow_id="workflow-123",
        status=WorkflowRunStatus.SUCCEEDED,
        artifacts=make_artifact_bundle(),
    )

    request = service.build_case_grounded_request(
        result=result,
        user_message="Summarize the evidence gaps.",
    )

    assert request.metadata["workflow_id"] == "workflow-123"
    assert request.messages[0].role == "system"
    assert "Reviewer question" in request.messages[1].content[0].text
    assert '"workflow_id": "workflow-123"' in request.messages[1].content[0].text
