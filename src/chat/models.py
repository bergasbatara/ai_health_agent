from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from domain.models import DomainModel


class ChatProvider(StrEnum):
    SILICONFLOW = "siliconflow"
    MOONSHOT = "moonshot"
    OTHER = "other"


class ChatMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatContentType(StrEnum):
    TEXT = "text"
    IMAGE_URL = "image_url"
    TOOL_RESULT = "tool_result"


class ChatTransportKind(StrEnum):
    REST = "rest"
    SSE = "sse"
    WEBSOCKET = "websocket"


class ChatModelFamily(StrEnum):
    KIMI_K2_6 = "kimi_k2_6"
    OTHER = "other"


class ChatToolChoiceMode(StrEnum):
    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"


class ChatReasoningMode(StrEnum):
    DEFAULT = "default"
    THINKING = "thinking"
    NON_THINKING = "non_thinking"


class ChatContentBlock(DomainModel):
    type: ChatContentType
    text: str | None = None
    image_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_block_payload(self) -> "ChatContentBlock":
        if self.type == ChatContentType.TEXT and not self.text:
            raise ValueError("text content blocks require text")
        if self.type == ChatContentType.IMAGE_URL and not self.image_url:
            raise ValueError("image_url content blocks require image_url")
        return self


class ChatMessage(DomainModel):
    role: ChatMessageRole
    content: list[ChatContentBlock] = Field(default_factory=list)
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, value: list[ChatContentBlock]) -> list[ChatContentBlock]:
        if not value:
            raise ValueError("chat messages must contain at least one content block")
        return value


class ChatToolDefinition(DomainModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ChatToolChoice(DomainModel):
    mode: ChatToolChoiceMode = ChatToolChoiceMode.AUTO
    tool_name: str | None = None

    @model_validator(mode="after")
    def validate_tool_choice(self) -> "ChatToolChoice":
        if self.mode == ChatToolChoiceMode.REQUIRED and not self.tool_name:
            raise ValueError("tool_name is required when tool choice mode is required")
        return self


class ChatGenerationConfig(DomainModel):
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=2048, ge=1, le=131072)
    reasoning_mode: ChatReasoningMode = ChatReasoningMode.DEFAULT
    stop_sequences: list[str] = Field(default_factory=list)

    @field_validator("stop_sequences")
    @classmethod
    def stop_sequences_must_be_non_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("stop_sequences must not contain blank entries")
        return value


class ChatModelCapabilities(DomainModel):
    supports_text_input: bool = True
    supports_image_input: bool = False
    supports_tool_use: bool = False
    supports_structured_output: bool = False
    supports_reasoning_modes: bool = False
    context_window_tokens: int | None = Field(default=None, ge=1)


class ChatModelRef(DomainModel):
    provider: ChatProvider
    family: ChatModelFamily = ChatModelFamily.OTHER
    model_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    transport: ChatTransportKind = ChatTransportKind.REST
    capabilities: ChatModelCapabilities = Field(default_factory=ChatModelCapabilities)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(DomainModel):
    model: ChatModelRef
    messages: list[ChatMessage] = Field(default_factory=list)
    generation: ChatGenerationConfig = Field(default_factory=ChatGenerationConfig)
    tools: list[ChatToolDefinition] = Field(default_factory=list)
    tool_choice: ChatToolChoice = Field(default_factory=ChatToolChoice)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("messages")
    @classmethod
    def messages_must_not_be_empty(cls, value: list[ChatMessage]) -> list[ChatMessage]:
        if not value:
            raise ValueError("chat requests must contain at least one message")
        return value


class ChatUsage(DomainModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def infer_total_tokens(self) -> "ChatUsage":
        self.total_tokens = self.input_tokens + self.output_tokens
        return self


class ChatToolCall(DomainModel):
    call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(DomainModel):
    model: ChatModelRef
    message: ChatMessage
    finish_reason: str = Field(default="stop", min_length=1)
    usage: ChatUsage = Field(default_factory=ChatUsage)
    tool_calls: list[ChatToolCall] = Field(default_factory=list)
    provider_response_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_siliconflow_kimi_k2_6_model(
    *,
    model_id: str = "moonshotai/Kimi-K2.6",
    base_url: str = "https://api.siliconflow.com/v1",
) -> ChatModelRef:
    return ChatModelRef(
        provider=ChatProvider.SILICONFLOW,
        family=ChatModelFamily.KIMI_K2_6,
        model_id=model_id,
        display_name="Kimi K2.6 via SiliconFlow",
        base_url=base_url,
        capabilities=ChatModelCapabilities(
            supports_text_input=True,
            supports_image_input=True,
            supports_tool_use=True,
            supports_structured_output=True,
            supports_reasoning_modes=True,
            context_window_tokens=256_000,
        ),
        metadata={
            "vendor": "moonshotai",
            "recommended_for": [
                "case_review_chat",
                "artifact_grounded_qa",
                "workflow_explanations",
            ],
        },
    )
