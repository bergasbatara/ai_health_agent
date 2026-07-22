from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import ApiServices, get_api_services, get_workflow_store
from api.models import CaseChatRequest, CaseChatResponse
from api.store import InMemoryWorkflowStore


chat_router = APIRouter(prefix="/cases/{workflow_id}", tags=["chat"])


@chat_router.post("/chat", response_model=CaseChatResponse)
def chat_with_case(
    workflow_id: str,
    payload: CaseChatRequest,
    services: ApiServices = Depends(get_api_services),
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> CaseChatResponse:
    result = store.get_result(workflow_id)
    response = services.answer_case_question(workflow_id=workflow_id, message=payload.message)
    return CaseChatResponse(
        workflow_id=workflow_id,
        status=result.status,
        chat_response=response,
    )
