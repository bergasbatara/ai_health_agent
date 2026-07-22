from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import (
    ChatContentBlock,
    ChatContentType,
    ChatMessage,
    ChatMessageRole,
    ChatModelRef,
    ChatProvider,
    ChatRequest,
    ChatResponse,
    ChatToolCall,
    ChatToolChoiceMode,
    ChatUsage,
    build_siliconflow_kimi_k2_6_model,
)


class ChatServiceError(RuntimeError):
    pass


class HttpResponse(Protocol):
    status_code: int
    text: str

    def json(self) -> dict[str, Any]:
        ...


class HttpClient(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: float,
    ) -> HttpResponse:
        ...


def _default_http_client():
    try:
        import httpx
    except ImportError as exc:
        raise ChatServiceError(
            "httpx is required for the chat service. Install dependencies with `pip install -e .`."
        ) from exc
    return httpx


def _map_content_block_to_siliconflow(block: ChatContentBlock) -> dict[str, Any]:
    if block.type == ChatContentType.TEXT:
        return {"type": "text", "text": block.text}
    if block.type == ChatContentType.IMAGE_URL:
        return {"type": "image_url", "image_url": {"url": block.image_url}}
    if block.type == ChatContentType.TOOL_RESULT:
        return {
            "type": "text",
            "text": block.text or json.dumps(block.metadata, ensure_ascii=True),
        }
    raise ChatServiceError(f"Unsupported content block type for SiliconFlow: {block.type}")


def map_message_to_siliconflow(message: ChatMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": message.role,
        "content": [_map_content_block_to_siliconflow(block) for block in message.content],
    }
    if message.name:
        payload["name"] = message.name
    if message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id
    return payload


def map_tool_definition_to_siliconflow(tool: Any) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def build_siliconflow_payload(request: ChatRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model.model_id,
        "messages": [map_message_to_siliconflow(message) for message in request.messages],
        "temperature": request.generation.temperature,
        "max_tokens": request.generation.max_output_tokens,
    }
    if request.generation.top_p is not None:
        payload["top_p"] = request.generation.top_p
    if request.generation.stop_sequences:
        payload["stop"] = request.generation.stop_sequences
    if request.tools:
        payload["tools"] = [map_tool_definition_to_siliconflow(tool) for tool in request.tools]

    if request.tool_choice.mode == ChatToolChoiceMode.NONE:
        payload["tool_choice"] = "none"
    elif request.tool_choice.mode == ChatToolChoiceMode.AUTO:
        payload["tool_choice"] = "auto"
    elif request.tool_choice.mode == ChatToolChoiceMode.REQUIRED:
        payload["tool_choice"] = {
            "type": "function",
            "function": {"name": request.tool_choice.tool_name},
        }

    if request.generation.reasoning_mode != "default":
        payload["extra_body"] = {"reasoning_mode": request.generation.reasoning_mode}

    return payload


def _map_siliconflow_content_item(item: Any) -> ChatContentBlock:
    if isinstance(item, str):
        return ChatContentBlock(type=ChatContentType.TEXT, text=item)
    if not isinstance(item, dict):
        return ChatContentBlock(type=ChatContentType.TEXT, text=str(item))

    item_type = item.get("type")
    if item_type == "text":
        return ChatContentBlock(type=ChatContentType.TEXT, text=str(item.get("text", "")))
    if item_type == "image_url":
        image_url = item.get("image_url")
        if isinstance(image_url, dict):
            image_url = image_url.get("url")
        return ChatContentBlock(type=ChatContentType.IMAGE_URL, image_url=str(image_url or ""))

    return ChatContentBlock(
        type=ChatContentType.TEXT,
        text=str(item.get("text") or item.get("content") or json.dumps(item, ensure_ascii=True)),
        metadata={"provider_item": item},
    )


def _map_siliconflow_message(payload: dict[str, Any]) -> ChatMessage:
    raw_content = payload.get("content", [])
    if isinstance(raw_content, str):
        content = [ChatContentBlock(type=ChatContentType.TEXT, text=raw_content)]
    else:
        content = [_map_siliconflow_content_item(item) for item in raw_content]
    return ChatMessage(
        role=payload.get("role", ChatMessageRole.ASSISTANT),
        content=content,
        name=payload.get("name"),
        metadata={"provider_message": payload},
    )


def _map_siliconflow_tool_calls(message: dict[str, Any]) -> list[ChatToolCall]:
    tool_calls: list[ChatToolCall] = []
    for item in message.get("tool_calls", []) or []:
        function = item.get("function", {}) if isinstance(item, dict) else {}
        raw_arguments = function.get("arguments", {})
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {"raw_arguments": raw_arguments}
        else:
            arguments = dict(raw_arguments or {})
        tool_calls.append(
            ChatToolCall(
                call_id=str(item.get("id", "")),
                tool_name=str(function.get("name", "")),
                arguments=arguments,
            )
        )
    return tool_calls


def map_siliconflow_response(response_payload: dict[str, Any], *, model: ChatModelRef) -> ChatResponse:
    choices = response_payload.get("choices") or []
    if not choices:
        raise ChatServiceError("SiliconFlow response did not contain choices")

    first_choice = choices[0] or {}
    message_payload = first_choice.get("message") or {"role": "assistant", "content": ""}
    usage_payload = response_payload.get("usage") or {}
    return ChatResponse(
        model=model,
        message=_map_siliconflow_message(message_payload),
        finish_reason=str(first_choice.get("finish_reason", "stop")),
        usage=ChatUsage(
            input_tokens=int(usage_payload.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage_payload.get("completion_tokens", 0) or 0),
        ),
        tool_calls=_map_siliconflow_tool_calls(message_payload),
        provider_response_id=response_payload.get("id"),
        metadata={"provider_response": response_payload},
    )


@dataclass(slots=True)
class SiliconFlowChatAdapter:
    api_key: str
    timeout_seconds: float = 60.0
    http_client: HttpClient | None = None
    endpoint_path: str = "/chat/completions"

    def _client(self):
        return self.http_client or _default_http_client()

    def generate(self, request: ChatRequest) -> ChatResponse:
        if request.model.provider != ChatProvider.SILICONFLOW:
            raise ChatServiceError(
                f"SiliconFlowChatAdapter cannot handle provider {request.model.provider}"
            )

        url = f"{request.model.base_url.rstrip('/')}{self.endpoint_path}"
        payload = build_siliconflow_payload(request)
        response = self._client().post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise ChatServiceError(
                f"SiliconFlow chat request failed with status {response.status_code}: {response.text}"
            )
        try:
            response_payload = response.json()
        except Exception as exc:
            raise ChatServiceError("SiliconFlow response was not valid JSON") from exc
        return map_siliconflow_response(response_payload, model=request.model)


@dataclass(slots=True)
class ChatServiceConfig:
    siliconflow_api_key: str
    siliconflow_base_url: str = "https://api.siliconflow.com/v1"
    siliconflow_model: str = "moonshotai/Kimi-K2.6"
    timeout_seconds: float = 60.0


@dataclass(slots=True)
class ChatService:
    config: ChatServiceConfig
    siliconflow_adapter: SiliconFlowChatAdapter = field(init=False)

    def __post_init__(self) -> None:
        self.siliconflow_adapter = SiliconFlowChatAdapter(
            api_key=self.config.siliconflow_api_key,
            timeout_seconds=self.config.timeout_seconds,
        )

    def build_default_model(self) -> ChatModelRef:
        return build_siliconflow_kimi_k2_6_model(
            model_id=self.config.siliconflow_model,
            base_url=self.config.siliconflow_base_url,
        )

    def generate(self, request: ChatRequest) -> ChatResponse:
        if request.model.provider == ChatProvider.SILICONFLOW:
            return self.siliconflow_adapter.generate(request)
        raise ChatServiceError(f"Unsupported chat provider: {request.model.provider}")


def load_chat_service_config_from_env() -> ChatServiceConfig:
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        raise ChatServiceError("SILICONFLOW_API_KEY is required for SiliconFlow chat")
    return ChatServiceConfig(
        siliconflow_api_key=api_key,
        siliconflow_base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1"),
        siliconflow_model=os.getenv("SILICONFLOW_MODEL", "moonshotai/Kimi-K2.6"),
    )
