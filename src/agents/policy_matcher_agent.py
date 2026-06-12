from __future__ import annotations

from .models import PolicyMatcherInput, PolicyMatcherOutput
from .prompts import POLICY_MATCHER_SYSTEM_PROMPT, build_policy_matcher_user_prompt
from .runtime import AgentResponseProvider, run_structured_agent


def run_policy_matcher_agent(
    agent_input: PolicyMatcherInput,
    *,
    provider: AgentResponseProvider,
    max_retries: int = 1,
) -> PolicyMatcherOutput:
    return run_structured_agent(
        provider=provider,
        system_prompt=POLICY_MATCHER_SYSTEM_PROMPT,
        user_prompt=build_policy_matcher_user_prompt(agent_input),
        response_model=PolicyMatcherOutput,
        max_retries=max_retries,
    )
