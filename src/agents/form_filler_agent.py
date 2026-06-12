from __future__ import annotations

from .models import FormFillerInput, FormFillerOutput
from .prompts import FORM_FILLER_SYSTEM_PROMPT, build_form_filler_user_prompt
from .runtime import AgentResponseProvider, run_structured_agent


def run_form_filler_agent(
    agent_input: FormFillerInput,
    *,
    provider: AgentResponseProvider,
    max_retries: int = 1,
) -> FormFillerOutput:
    return run_structured_agent(
        provider=provider,
        system_prompt=FORM_FILLER_SYSTEM_PROMPT,
        user_prompt=build_form_filler_user_prompt(agent_input),
        response_model=FormFillerOutput,
        max_retries=max_retries,
    )
