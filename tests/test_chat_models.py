import pytest

from chat import (
    ChatContentBlock,
    ChatContentType,
    ChatMessage,
    ChatMessageRole,
    ChatReasoningMode,
    ChatRequest,
    ChatToolChoice,
    ChatToolChoiceMode,
    ChatUsage,
    build_siliconflow_kimi_k2_6_model,
)


def test_build_siliconflow_kimi_k2_6_model_returns_flexible_model_ref():
    model = build_siliconflow_kimi_k2_6_model()

    assert model.provider == "siliconflow"
    assert model.family == "kimi_k2_6"
    assert model.model_id == "moonshotai/Kimi-K2.6"
    assert model.capabilities.supports_image_input is True
    assert model.capabilities.supports_tool_use is True
    assert model.capabilities.context_window_tokens == 256_000


def test_chat_request_accepts_non_openai_message_shape():
    model = build_siliconflow_kimi_k2_6_model()

    request = ChatRequest(
        model=model,
        messages=[
            ChatMessage(
                role=ChatMessageRole.USER,
                content=[
                    ChatContentBlock(type=ChatContentType.TEXT, text="Explain the policy match result."),
                ],
            )
        ],
        generation={"reasoning_mode": ChatReasoningMode.THINKING, "max_output_tokens": 4096},
    )

    assert request.generation.reasoning_mode == "thinking"
    assert request.messages[0].content[0].text == "Explain the policy match result."


def test_chat_tool_choice_requires_tool_name_for_required_mode():
    with pytest.raises(ValueError, match="tool_name is required"):
        ChatToolChoice(mode=ChatToolChoiceMode.REQUIRED)


def test_chat_usage_infers_total_tokens():
    usage = ChatUsage(input_tokens=120, output_tokens=80)

    assert usage.total_tokens == 200


def test_text_content_block_requires_text():
    with pytest.raises(ValueError, match="text content blocks require text"):
        ChatContentBlock(type=ChatContentType.TEXT)
