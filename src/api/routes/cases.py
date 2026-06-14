from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_workflow_store
from api.models import CaseSummaryResponse, SubmitCaseRequest, SubmitCaseResponse, build_case_summary_response
from api.store import InMemoryWorkflowStore, WorkflowResultNotFoundError
from app.run_prior_auth import build_default_crews, build_mock_crews, build_searcher_from_data_dir
from orchestration import run_prior_auth_workflow_with_crewai


cases_router = APIRouter(prefix="/cases", tags=["cases"])


def _execute_workflow(request: SubmitCaseRequest):
    searcher = build_searcher_from_data_dir(request.data_dir)
    if request.use_mock_crews:
        extractor_crew, policy_matcher_crew, form_filler_crew = build_mock_crews()
    else:
        extractor_crew, policy_matcher_crew, form_filler_crew = build_default_crews(
            model=request.model,
            verbose=False,
        )
    workflow_id = request.workflow_id or f"prior-auth-{uuid4().hex[:12]}"
    return run_prior_auth_workflow_with_crewai(
        workflow_id=workflow_id,
        case_path=request.case_path,
        retrieval_searcher=searcher,
        extractor_crew=extractor_crew,
        policy_matcher_crew=policy_matcher_crew,
        form_filler_crew=form_filler_crew,
        retrieval_top_k=request.top_k,
    )


@cases_router.post("", response_model=SubmitCaseResponse, status_code=status.HTTP_201_CREATED)
def submit_case(
    payload: SubmitCaseRequest,
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> SubmitCaseResponse:
    result = _execute_workflow(payload)
    store.save_result(result)
    return SubmitCaseResponse(
        workflow=build_case_summary_response(result),
        result=result,
    )


@cases_router.get("", response_model=list[CaseSummaryResponse])
def list_cases(
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> list[CaseSummaryResponse]:
    return [build_case_summary_response(result) for result in store.list_results()]


@cases_router.get("/{workflow_id}", response_model=CaseSummaryResponse)
def get_case_status(
    workflow_id: str,
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> CaseSummaryResponse:
    try:
        result = store.get_result(workflow_id)
    except WorkflowResultNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return build_case_summary_response(result)
