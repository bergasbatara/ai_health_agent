from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from agents.runtime import AgentResponseProvider

from .handlers import (
    handle_case_intake,
    handle_draft_generation,
    handle_fact_extraction,
    handle_policy_matching,
    handle_policy_retrieval,
    handle_rules_validation,
)
from .models import (
    RetryPolicy,
    StepExecutionRecord,
    StepStatus,
    WorkflowArtifactBundle,
    WorkflowResult,
    WorkflowRunStatus,
    WorkflowState,
    WorkflowStep,
)
from .policies import (
    classify_workflow_exception,
    make_human_review_failure,
    resolve_terminal_workflow_status,
    should_require_human_review,
    should_retry_step,
)
from .steps import WORKFLOW_STEP_ORDER


class WorkflowEngineError(RuntimeError):
    pass


@dataclass(slots=True)
class WorkflowRunInputs:
    case_path: str
    retrieval_searcher: object
    extractor_provider: AgentResponseProvider
    policy_matcher_provider: AgentResponseProvider
    form_filler_provider: AgentResponseProvider
    retrieval_top_k: int = 5
    retrieval_embed_texts_fn: Callable[[list[str]], list[list[float]]] | None = None
    agent_max_retries_per_call: int = 0


class WorkflowEngine:
    def run(
        self,
        workflow_id: str,
        run_inputs: WorkflowRunInputs,
        *,
        retry_policy: RetryPolicy | None = None,
    ) -> WorkflowResult:
        state = WorkflowState(
            workflow_id=workflow_id,
            status=WorkflowRunStatus.RUNNING,
            current_step=WORKFLOW_STEP_ORDER[0],
            retry_policy=retry_policy or RetryPolicy(
                retryable_steps=[
                    WorkflowStep.FACT_EXTRACTION,
                    WorkflowStep.POLICY_RETRIEVAL,
                    WorkflowStep.POLICY_MATCHING,
                    WorkflowStep.DRAFT_GENERATION,
                ]
            ),
        )

        for step in WORKFLOW_STEP_ORDER:
            terminal_result = self._run_step_with_retries(state, step, run_inputs)
            if terminal_result is not None:
                return terminal_result

        state.current_step = None
        state.status = resolve_terminal_workflow_status(
            failures=state.failures,
            rules_result=state.artifacts.rules_result,
        )
        state.updated_at = self._now()
        return self._build_result(state)

    def _run_step_with_retries(
        self,
        state: WorkflowState,
        step: WorkflowStep,
        run_inputs: WorkflowRunInputs,
    ) -> WorkflowResult | None:
        attempts = 0
        while True:
            attempts += 1
            state.current_step = step
            state.status = WorkflowRunStatus.RUNNING
            started_at = self._now()

            try:
                artifacts = self._execute_step(step, state, run_inputs)
            except Exception as exc:
                failure = classify_workflow_exception(step, exc, retry_count=attempts - 1)
                state.failures.append(failure)
                state.step_history.append(
                    StepExecutionRecord(
                        step=step,
                        status=StepStatus.FAILED,
                        attempts=attempts,
                        started_at=started_at,
                        completed_at=self._now(),
                        failure=failure,
                        notes=failure.message,
                    )
                )
                state.updated_at = self._now()

                if should_retry_step(step, failure, state.retry_policy, attempts_so_far=attempts):
                    continue

                state.current_step = None
                state.status = resolve_terminal_workflow_status(
                    failures=state.failures,
                    rules_result=state.artifacts.rules_result,
                )
                return self._build_result(state)

            self._merge_artifacts(state, artifacts)
            state.step_history.append(
                StepExecutionRecord(
                    step=step,
                    status=StepStatus.SUCCEEDED,
                    attempts=attempts,
                    started_at=started_at,
                    completed_at=self._now(),
                )
            )
            state.updated_at = self._now()

            if step == WorkflowStep.RULES_VALIDATION and state.artifacts.rules_result is not None:
                if should_require_human_review(state.artifacts.rules_result):
                    failure = make_human_review_failure(
                        WorkflowStep.RULES_VALIDATION,
                        message="Rules validation requires human review before submission.",
                        issues=state.artifacts.rules_result.issues,
                    )
                    state.failures.append(failure)
                    state.current_step = None
                    state.status = resolve_terminal_workflow_status(
                        failures=state.failures,
                        rules_result=state.artifacts.rules_result,
                    )
                    return self._build_result(state)
            return None

    def _execute_step(
        self,
        step: WorkflowStep,
        state: WorkflowState,
        run_inputs: WorkflowRunInputs,
    ) -> WorkflowArtifactBundle:
        artifacts = state.artifacts

        if step == WorkflowStep.CASE_INTAKE:
            return handle_case_intake(run_inputs.case_path)

        if step == WorkflowStep.FACT_EXTRACTION:
            patient_case = self._require_artifact(artifacts.patient_case, "patient_case", step)
            return handle_fact_extraction(
                patient_case,
                provider=run_inputs.extractor_provider,
                max_retries=run_inputs.agent_max_retries_per_call,
            )

        if step == WorkflowStep.POLICY_RETRIEVAL:
            patient_case = self._require_artifact(artifacts.patient_case, "patient_case", step)
            return handle_policy_retrieval(
                patient_case,
                searcher=run_inputs.retrieval_searcher,
                top_k=run_inputs.retrieval_top_k,
                embed_texts_fn=run_inputs.retrieval_embed_texts_fn,
            )

        if step == WorkflowStep.POLICY_MATCHING:
            patient_case = self._require_artifact(artifacts.patient_case, "patient_case", step)
            extracted_facts = self._require_artifact(artifacts.extracted_facts, "extracted_facts", step)
            retrieval_result = self._require_artifact(artifacts.retrieval_result, "retrieval_result", step)
            return handle_policy_matching(
                patient_case,
                extracted_facts,
                retrieval_result.evidence,
                provider=run_inputs.policy_matcher_provider,
                max_retries=run_inputs.agent_max_retries_per_call,
            )

        if step == WorkflowStep.DRAFT_GENERATION:
            patient_case = self._require_artifact(artifacts.patient_case, "patient_case", step)
            extracted_facts = self._require_artifact(artifacts.extracted_facts, "extracted_facts", step)
            policy_match_result = self._require_artifact(artifacts.policy_match_result, "policy_match_result", step)
            return handle_draft_generation(
                patient_case,
                extracted_facts,
                policy_match_result,
                provider=run_inputs.form_filler_provider,
                max_retries=run_inputs.agent_max_retries_per_call,
            )

        if step == WorkflowStep.RULES_VALIDATION:
            patient_case = self._require_artifact(artifacts.patient_case, "patient_case", step)
            extracted_facts = self._require_artifact(artifacts.extracted_facts, "extracted_facts", step)
            policy_match_result = self._require_artifact(artifacts.policy_match_result, "policy_match_result", step)
            prior_auth_draft = self._require_artifact(artifacts.prior_auth_draft, "prior_auth_draft", step)
            return handle_rules_validation(
                patient_case,
                extracted_facts,
                policy_match_result,
                prior_auth_draft,
            )

        raise WorkflowEngineError(f"Unsupported workflow step: {step}")

    def _merge_artifacts(self, state: WorkflowState, partial_artifacts: WorkflowArtifactBundle) -> None:
        merged = state.artifacts.model_dump()
        merged.update(partial_artifacts.model_dump(exclude_none=True))
        state.artifacts = WorkflowArtifactBundle.model_validate(merged)
        if state.artifacts.rules_result is not None:
            state.issues = list(state.artifacts.rules_result.issues)

    def _build_result(self, state: WorkflowState) -> WorkflowResult:
        return WorkflowResult(
            workflow_id=state.workflow_id,
            status=state.status,
            artifacts=state.artifacts,
            issues=state.issues,
            failures=state.failures,
            step_history=state.step_history,
        )

    def _require_artifact(self, value: object | None, artifact_name: str, step: WorkflowStep):
        if value is None:
            raise WorkflowEngineError(
                f"Required artifact '{artifact_name}' was missing before step '{step}'."
            )
        return value

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)


def run_workflow(
    workflow_id: str,
    run_inputs: WorkflowRunInputs,
    *,
    retry_policy: RetryPolicy | None = None,
) -> WorkflowResult:
    return WorkflowEngine().run(
        workflow_id,
        run_inputs,
        retry_policy=retry_policy,
    )
