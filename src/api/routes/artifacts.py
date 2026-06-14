from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_workflow_store
from api.models import DraftOutputResponse, ExtractedFactsResponse, PolicyEvidenceResponse, PolicyMatchResponse
from api.store import InMemoryWorkflowStore


artifacts_router = APIRouter(prefix="/cases/{workflow_id}", tags=["artifacts"])


def _get_result_or_404(workflow_id: str, store: InMemoryWorkflowStore):
    return store.get_result(workflow_id)


@artifacts_router.get("/facts", response_model=ExtractedFactsResponse)
def get_extracted_facts(
    workflow_id: str,
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> ExtractedFactsResponse:
    result = _get_result_or_404(workflow_id, store)
    return ExtractedFactsResponse(
        workflow_id=result.workflow_id,
        status=result.status,
        extracted_facts=result.artifacts.extracted_facts,
    )


@artifacts_router.get("/evidence", response_model=PolicyEvidenceResponse)
def get_policy_evidence(
    workflow_id: str,
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> PolicyEvidenceResponse:
    result = _get_result_or_404(workflow_id, store)
    return PolicyEvidenceResponse(
        workflow_id=result.workflow_id,
        status=result.status,
        retrieval_result=result.artifacts.retrieval_result,
    )


@artifacts_router.get("/policy-match", response_model=PolicyMatchResponse)
def get_policy_match(
    workflow_id: str,
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> PolicyMatchResponse:
    result = _get_result_or_404(workflow_id, store)
    return PolicyMatchResponse(
        workflow_id=result.workflow_id,
        status=result.status,
        policy_match_result=result.artifacts.policy_match_result,
    )


@artifacts_router.get("/draft", response_model=DraftOutputResponse)
def get_draft_output(
    workflow_id: str,
    store: InMemoryWorkflowStore = Depends(get_workflow_store),
) -> DraftOutputResponse:
    result = _get_result_or_404(workflow_id, store)
    return DraftOutputResponse(
        workflow_id=result.workflow_id,
        status=result.status,
        prior_auth_draft=result.artifacts.prior_auth_draft,
    )
