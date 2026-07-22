from fastapi.testclient import TestClient

from api.app import create_app
from chat import ChatContentBlock, ChatContentType, ChatMessage, ChatMessageRole, ChatUsage
from chat.service import ChatResponse, ChatServiceConfig, ChatService
from tests.test_api_cases_route import make_case_file


class StubChatService:
    def answer_case_question(self, *, result, user_message: str):
        return ChatResponse(
            model=ChatService(ChatServiceConfig(siliconflow_api_key="secret")).build_default_model(),
            message=ChatMessage(
                role=ChatMessageRole.ASSISTANT,
                content=[ChatContentBlock(type=ChatContentType.TEXT, text=f"Echo: {user_message}")],
            ),
            usage=ChatUsage(input_tokens=10, output_tokens=5),
        )


def test_chat_with_case_returns_grounded_chat_response(tmp_path):
    app = create_app()
    app.state.api_services.chat_service = StubChatService()
    client = TestClient(app)

    case_path = make_case_file(tmp_path)
    submit_response = client.post(
        "/cases",
        json={
            "case_path": case_path,
            "data_dir": "data",
            "use_mock_crews": True,
            "top_k": 3,
        },
    )
    workflow_id = submit_response.json()["workflow"]["workflow_id"]

    response = client.post(
        f"/cases/{workflow_id}/chat",
        json={"message": "Why was this case approved?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == workflow_id
    assert payload["chat_response"]["message"]["content"][0]["text"] == "Echo: Why was this case approved?"
