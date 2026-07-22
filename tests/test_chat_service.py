import pytest

from chat import (
    ChatContentBlock,
    ChatContentType,
    ChatMessage,
    ChatMessageRole,
    ChatRequest,
    ChatToolChoice,
    ChatToolChoiceMode,
    ChatToolDefinition,
    build_siliconflow_kimi_k2_6_model,
)
from chat.service import (
    ChatServiceError,
    SiliconFlowChatAdapter,
    build_siliconflow_payload,
    load_chat_service_config_from_env,
    map_siliconflow_response,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str | None = None):
        self.status_code = status_code
        self._payload = payload
        self.text = text or ""

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[dict] = []

    def post(self, url: str, *, headers: dict[str, str], json: dict, timeout: float):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return self.response


def make_request() -> ChatRequest:
    return ChatRequest(
        model=build_siliconflow_kimi_k2_6_model(),
        messages=[
            ChatMessage(
                role=ChatMessageRole.SYSTEM,
                content=[ChatContentBlock(type=ChatContentType.TEXT, text="You are a case review assistant.")],
            ),
            ChatMessage(
                role=ChatMessageRole.USER,
                content=[ChatContentBlock(type=ChatContentType.TEXT, text="Explain this denial risk.")],
            ),
        ],
    )


def test_build_siliconflow_payload_maps_internal_request_shape():
    request = make_request()
    request.tools = [
        ChatToolDefinition(
            name="lookup_policy",
            description="Lookup policy evidence",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )
    ]
    request.tool_choice = ChatToolChoice(mode=ChatToolChoiceMode.REQUIRED, tool_name="lookup_policy")

    payload = build_siliconflow_payload(request)

    assert payload["model"] == "moonshotai/Kimi-K2.6"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"][0]["text"] == "Explain this denial risk."
    assert payload["tools"][0]["function"]["name"] == "lookup_policy"
    assert payload["tool_choice"]["function"]["name"] == "lookup_policy"


def test_map_siliconflow_response_maps_back_to_internal_shape():
    model = build_siliconflow_kimi_k2_6_model()
    payload = {
        "id": "resp_123",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "The case meets conservative therapy criteria."}
                    ],
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "lookup_policy",
                                "arguments": '{"query":"knee MRI conservative therapy"}',
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 45},
    }

    response = map_siliconflow_response(payload, model=model)

    assert response.provider_response_id == "resp_123"
    assert response.message.role == "assistant"
    assert response.message.content[0].text == "The case meets conservative therapy criteria."
    assert response.usage.total_tokens == 165
    assert response.tool_calls[0].tool_name == "lookup_policy"


def test_siliconflow_adapter_posts_and_returns_chat_response():
    response_payload = {
        "id": "resp_456",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Grounded answer."},
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    fake_client = FakeHttpClient(FakeResponse(200, response_payload))
    adapter = SiliconFlowChatAdapter(api_key="secret", http_client=fake_client)

    response = adapter.generate(make_request())

    assert fake_client.calls[0]["url"] == "https://api.siliconflow.com/v1/chat/completions"
    assert fake_client.calls[0]["headers"]["Authorization"] == "Bearer secret"
    assert response.message.content[0].text == "Grounded answer."


def test_siliconflow_adapter_raises_on_http_error():
    fake_client = FakeHttpClient(FakeResponse(429, {}, text="rate limited"))
    adapter = SiliconFlowChatAdapter(api_key="secret", http_client=fake_client)

    with pytest.raises(ChatServiceError, match="status 429"):
        adapter.generate(make_request())


def test_load_chat_service_config_from_env_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)

    with pytest.raises(ChatServiceError, match="SILICONFLOW_API_KEY is required"):
        load_chat_service_config_from_env()
