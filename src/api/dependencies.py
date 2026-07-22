from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from chat.service import ChatService, ChatServiceError, load_chat_service_config_from_env
from .errors import WorkflowExecutionError
from api.models import SubmitCaseRequest
from .store import InMemoryWorkflowStore
from app.run_prior_auth import build_default_crews, build_mock_crews, build_searcher_from_data_dir
from orchestration import WorkflowResult, run_prior_auth_workflow_with_crewai


def get_workflow_store(request: Request) -> InMemoryWorkflowStore:
    return request.app.state.workflow_store


@dataclass(slots=True)
class ApiServices:
    workflow_store: InMemoryWorkflowStore
    chat_service: ChatService | None = None

    def run_workflow(self, request: SubmitCaseRequest) -> WorkflowResult:
        try:
            searcher = build_searcher_from_data_dir(request.data_dir)
            if request.use_mock_crews:
                extractor_crew, policy_matcher_crew, form_filler_crew = build_mock_crews()
            else:
                extractor_crew, policy_matcher_crew, form_filler_crew = build_default_crews(
                    model=request.model,
                    verbose=False,
                )

            workflow_id = request.workflow_id
            if workflow_id is None:
                from uuid import uuid4

                workflow_id = f"prior-auth-{uuid4().hex[:12]}"

            result = run_prior_auth_workflow_with_crewai(
                workflow_id=workflow_id,
                case_path=request.case_path,
                retrieval_searcher=searcher,
                extractor_crew=extractor_crew,
                policy_matcher_crew=policy_matcher_crew,
                form_filler_crew=form_filler_crew,
                retrieval_top_k=request.top_k,
            )
            self.workflow_store.save_result(result)
            return result
        except Exception as exc:
            raise WorkflowExecutionError(str(exc)) from exc

    def answer_case_question(self, *, workflow_id: str, message: str):
        result = self.workflow_store.get_result(workflow_id)
        if self.chat_service is None:
            raise WorkflowExecutionError(
                "Chat service is not configured. Set SILICONFLOW_API_KEY and restart the backend."
            )
        try:
            return self.chat_service.answer_case_question(result=result, user_message=message)
        except ChatServiceError as exc:
            raise WorkflowExecutionError(str(exc)) from exc


def get_api_services(request: Request) -> ApiServices:
    return request.app.state.api_services


def build_api_services(*, workflow_store: InMemoryWorkflowStore) -> ApiServices:
    chat_service = None
    try:
        chat_service = ChatService(load_chat_service_config_from_env())
    except ChatServiceError:
        chat_service = None
    return ApiServices(workflow_store=workflow_store, chat_service=chat_service)
