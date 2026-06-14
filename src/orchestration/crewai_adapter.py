from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agents.runtime import AgentResponseProvider

from .models import RetryPolicy, WorkflowResult
from .service import OrchestrationService


class CrewAIAdapterError(RuntimeError):
    pass


class CrewRunnable(Protocol):
    def kickoff(self, inputs: dict[str, Any] | None = None) -> Any:
        ...


def is_crewai_available() -> bool:
    try:
        import crewai  # noqa: F401
    except ImportError:
        return False
    return True


def _coerce_crewai_output_to_text(output: Any) -> str:
    if output is None:
        raise CrewAIAdapterError("CrewAI returned no output.")
    if isinstance(output, str):
        return output

    for attr_name in ("raw", "result", "output"):
        value = getattr(output, attr_name, None)
        if isinstance(value, str) and value.strip():
            return value

    text = str(output).strip()
    if not text:
        raise CrewAIAdapterError("CrewAI output could not be converted to text.")
    return text


class CrewAIResponseProvider:
    def __init__(
        self,
        crew: CrewRunnable,
        *,
        static_inputs: dict[str, Any] | None = None,
    ) -> None:
        self.crew = crew
        self.static_inputs = dict(static_inputs or {})

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        output = self.crew.kickoff(
            inputs={
                **self.static_inputs,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return _coerce_crewai_output_to_text(output)


@dataclass(slots=True)
class CrewAIWorkflowProviders:
    extractor_provider: AgentResponseProvider
    policy_matcher_provider: AgentResponseProvider
    form_filler_provider: AgentResponseProvider


class CrewAIOrchestrationAdapter:
    def __init__(self, *, service: OrchestrationService | None = None) -> None:
        self.service = service or OrchestrationService()

    def make_provider(
        self,
        crew: CrewRunnable,
        *,
        static_inputs: dict[str, Any] | None = None,
    ) -> CrewAIResponseProvider:
        return CrewAIResponseProvider(crew, static_inputs=static_inputs)

    def run_with_crews(
        self,
        *,
        workflow_id: str,
        case_path: str,
        retrieval_searcher: object,
        extractor_crew: CrewRunnable,
        policy_matcher_crew: CrewRunnable,
        form_filler_crew: CrewRunnable,
        retry_policy: RetryPolicy | None = None,
        retrieval_top_k: int | None = None,
        retrieval_embed_texts_fn=None,
        agent_max_retries_per_call: int | None = None,
        extractor_static_inputs: dict[str, Any] | None = None,
        policy_matcher_static_inputs: dict[str, Any] | None = None,
        form_filler_static_inputs: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        return self.service.run_prior_auth_workflow(
            workflow_id=workflow_id,
            case_path=case_path,
            retrieval_searcher=retrieval_searcher,
            extractor_provider=self.make_provider(
                extractor_crew,
                static_inputs=extractor_static_inputs,
            ),
            policy_matcher_provider=self.make_provider(
                policy_matcher_crew,
                static_inputs=policy_matcher_static_inputs,
            ),
            form_filler_provider=self.make_provider(
                form_filler_crew,
                static_inputs=form_filler_static_inputs,
            ),
            retry_policy=retry_policy,
            retrieval_top_k=retrieval_top_k,
            retrieval_embed_texts_fn=retrieval_embed_texts_fn,
            agent_max_retries_per_call=agent_max_retries_per_call,
        )


def run_prior_auth_workflow_with_crewai(
    *,
    workflow_id: str,
    case_path: str,
    retrieval_searcher: object,
    extractor_crew: CrewRunnable,
    policy_matcher_crew: CrewRunnable,
    form_filler_crew: CrewRunnable,
    service: OrchestrationService | None = None,
    retry_policy: RetryPolicy | None = None,
    retrieval_top_k: int | None = None,
    retrieval_embed_texts_fn=None,
    agent_max_retries_per_call: int | None = None,
    extractor_static_inputs: dict[str, Any] | None = None,
    policy_matcher_static_inputs: dict[str, Any] | None = None,
    form_filler_static_inputs: dict[str, Any] | None = None,
) -> WorkflowResult:
    return CrewAIOrchestrationAdapter(service=service).run_with_crews(
        workflow_id=workflow_id,
        case_path=case_path,
        retrieval_searcher=retrieval_searcher,
        extractor_crew=extractor_crew,
        policy_matcher_crew=policy_matcher_crew,
        form_filler_crew=form_filler_crew,
        retry_policy=retry_policy,
        retrieval_top_k=retrieval_top_k,
        retrieval_embed_texts_fn=retrieval_embed_texts_fn,
        agent_max_retries_per_call=agent_max_retries_per_call,
        extractor_static_inputs=extractor_static_inputs,
        policy_matcher_static_inputs=policy_matcher_static_inputs,
        form_filler_static_inputs=form_filler_static_inputs,
    )
