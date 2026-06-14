from __future__ import annotations

from fastapi import APIRouter, Depends, status

from api.dependencies import ApiServices, get_api_services, get_workflow_store
from api.models import CaseSummaryResponse, SubmitCaseRequest, SubmitCaseResponse, build_case_summary_response
from api.store import InMemoryWorkflowStore


cases_router = APIRouter(prefix="/cases", tags=["cases"])


@cases_router.post("", response_model=SubmitCaseResponse, status_code=status.HTTP_201_CREATED)
def submit_case(
    payload: SubmitCaseRequest,
    services: ApiServices = Depends(get_api_services),
) -> SubmitCaseResponse:
    result = services.run_workflow(payload)
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
    result = store.get_result(workflow_id)
    return build_case_summary_response(result)
