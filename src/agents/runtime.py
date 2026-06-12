from __future__ import annotations

import json
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError


class AgentRuntimeError(RuntimeError):
    pass


class AgentResponseProvider(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        ...


class StaticResponseProvider:
    def __init__(self, responses: list[str] | None = None):
        self._responses = list(responses or [])

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        if not self._responses:
            raise AgentRuntimeError("No static responses configured for provider")
        return self._responses.pop(0)


ModelT = TypeVar("ModelT", bound=BaseModel)


def parse_structured_output(raw_output: str, response_model: type[ModelT]) -> ModelT:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise AgentRuntimeError(f"Agent output was not valid JSON: {exc.msg}") from exc

    try:
        return response_model.model_validate(payload)
    except ValidationError as exc:
        raise AgentRuntimeError(f"Agent output did not match expected schema: {exc}") from exc


def run_structured_agent(
    *,
    provider: AgentResponseProvider,
    system_prompt: str,
    user_prompt: str,
    response_model: type[ModelT],
    max_retries: int = 1,
) -> ModelT:
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")

    last_error: Exception | None = None
    for _ in range(max_retries + 1):
        raw_output = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        try:
            return parse_structured_output(raw_output, response_model)
        except AgentRuntimeError as exc:
            last_error = exc

    raise AgentRuntimeError(f"Structured agent failed after retries: {last_error}")
