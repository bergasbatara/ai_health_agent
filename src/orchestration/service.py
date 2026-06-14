from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from agents.runtime import AgentResponseProvider

from .engine import WorkflowEngine, WorkflowRunInputs
from .models import RetryPolicy, WorkflowResult, WorkflowStep


@dataclass(slots=True)
class OrchestrationServiceConfig:
    retry_policy: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(
            retryable_steps=[
                WorkflowStep.FACT_EXTRACTION,
                WorkflowStep.POLICY_RETRIEVAL,
                WorkflowStep.POLICY_MATCHING,
                WorkflowStep.DRAFT_GENERATION,
            ]
        )
    )
    retrieval_top_k: int = 5
    agent_max_retries_per_call: int = 0
    retrieval_embed_texts_fn: Callable[[list[str]], list[list[float]]] | None = None


class OrchestrationService:
    def __init__(
        self,
        *,
        engine: WorkflowEngine | None = None,
        config: OrchestrationServiceConfig | None = None,
    ) -> None:
        self.engine = engine or WorkflowEngine()
        self.config = config or OrchestrationServiceConfig()

    def run_prior_auth_workflow(
        self,
        *,
        workflow_id: str,
        case_path: str,
        retrieval_searcher: object,
        extractor_provider: AgentResponseProvider,
        policy_matcher_provider: AgentResponseProvider,
        form_filler_provider: AgentResponseProvider,
        retry_policy: RetryPolicy | None = None,
        retrieval_top_k: int | None = None,
        retrieval_embed_texts_fn: Callable[[list[str]], list[list[float]]] | None = None,
        agent_max_retries_per_call: int | None = None,
    ) -> WorkflowResult:
        run_inputs = WorkflowRunInputs(
            case_path=case_path,
            retrieval_searcher=retrieval_searcher,
            extractor_provider=extractor_provider,
            policy_matcher_provider=policy_matcher_provider,
            form_filler_provider=form_filler_provider,
            retrieval_top_k=retrieval_top_k if retrieval_top_k is not None else self.config.retrieval_top_k,
            retrieval_embed_texts_fn=(
                retrieval_embed_texts_fn
                if retrieval_embed_texts_fn is not None
                else self.config.retrieval_embed_texts_fn
            ),
            agent_max_retries_per_call=(
                agent_max_retries_per_call
                if agent_max_retries_per_call is not None
                else self.config.agent_max_retries_per_call
            ),
        )
        return self.engine.run(
            workflow_id,
            run_inputs,
            retry_policy=retry_policy or self.config.retry_policy,
        )


def run_prior_auth_workflow(
    *,
    workflow_id: str,
    case_path: str,
    retrieval_searcher: object,
    extractor_provider: AgentResponseProvider,
    policy_matcher_provider: AgentResponseProvider,
    form_filler_provider: AgentResponseProvider,
    retry_policy: RetryPolicy | None = None,
    retrieval_top_k: int = 5,
    retrieval_embed_texts_fn: Callable[[list[str]], list[list[float]]] | None = None,
    agent_max_retries_per_call: int = 0,
) -> WorkflowResult:
    service = OrchestrationService(
        config=OrchestrationServiceConfig(
            retry_policy=retry_policy
            or RetryPolicy(
                retryable_steps=[
                    WorkflowStep.FACT_EXTRACTION,
                    WorkflowStep.POLICY_RETRIEVAL,
                    WorkflowStep.POLICY_MATCHING,
                    WorkflowStep.DRAFT_GENERATION,
                ]
            ),
            retrieval_top_k=retrieval_top_k,
            retrieval_embed_texts_fn=retrieval_embed_texts_fn,
            agent_max_retries_per_call=agent_max_retries_per_call,
        )
    )
    return service.run_prior_auth_workflow(
        workflow_id=workflow_id,
        case_path=case_path,
        retrieval_searcher=retrieval_searcher,
        extractor_provider=extractor_provider,
        policy_matcher_provider=policy_matcher_provider,
        form_filler_provider=form_filler_provider,
        retry_policy=retry_policy,
        retrieval_top_k=retrieval_top_k,
        retrieval_embed_texts_fn=retrieval_embed_texts_fn,
        agent_max_retries_per_call=agent_max_retries_per_call,
    )
