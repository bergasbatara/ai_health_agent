from __future__ import annotations

from .models import ExtractorInput, ExtractorOutput
from .prompts import EXTRACTOR_SYSTEM_PROMPT, build_extractor_user_prompt
from .runtime import AgentResponseProvider, run_structured_agent


def run_extractor_agent(
    agent_input: ExtractorInput,
    *,
    provider: AgentResponseProvider,
    max_retries: int = 1,
) -> ExtractorOutput:
    return run_structured_agent(
        provider=provider,
        system_prompt=EXTRACTOR_SYSTEM_PROMPT,
        user_prompt=build_extractor_user_prompt(agent_input),
        response_model=ExtractorOutput,
        max_retries=max_retries,
    )
