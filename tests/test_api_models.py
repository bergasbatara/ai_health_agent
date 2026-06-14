from api import (
    CaseSummaryResponse,
    DraftOutputResponse,
    ExtractedFactsResponse,
    HealthResponse,
    PolicyEvidenceResponse,
    PolicyMatchResponse,
    SubmitCaseRequest,
    build_case_summary_response,
)
from domain import (
    BodyRegion,
    ClinicalStatus,
    CoverageCriterion,
    CriterionStatus,
    ExtractedClinicalFacts,
    ImagingModality,
    Laterality,
    PolicyEvidence,
    PolicyMatchResult,
    PriorAuthDraft,
    RecommendationSignal,
    ReviewStatus,
    PayerId,
)
from orchestration import WorkflowResult, WorkflowRunStatus
from retrieval import PolicySearchQuery, RetrievalResult, RetrievedChunk


def make_policy_evidence() -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id="evidence-1",
        document_id="aetna-knee-mri-policy",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
        relevance_score=0.91,
        page_number=2,
    )


def make_workflow_result() -> WorkflowResult:
    evidence = make_policy_evidence()
    return WorkflowResult(
        workflow_id="workflow-001",
        status=WorkflowRunStatus.SUCCEEDED,
        artifacts={
            "patient_case": {
                "case_id": "case-001",
                "payer_id": "aetna",
                "payer_name": "Aetna",
                "requested_modality": "mri",
                "requested_body_region": "knee",
                "requested_laterality": "left",
                "ordering_specialty": "orthopedics",
                "raw_clinical_note": "Knee pain.",
            }
        },
        issues=[],
        failures=[],
        step_history=[
            {
                "step": "case_intake",
                "status": "succeeded",
                "attempts": 1,
            }
        ],
    )


def test_submit_case_request_validates_required_case_path():
    request = SubmitCaseRequest(case_path="tmp/case-001.json")

    assert request.case_path == "tmp/case-001.json"
    assert request.top_k == 5
    assert request.use_mock_crews is False


def test_build_case_summary_response_maps_workflow_result():
    summary = build_case_summary_response(make_workflow_result())

    assert isinstance(summary, CaseSummaryResponse)
    assert summary.workflow_id == "workflow-001"
    assert summary.case_id == "case-001"
    assert summary.status == WorkflowRunStatus.SUCCEEDED
    assert summary.current_step == "case_intake"


def test_artifact_responses_accept_domain_artifacts():
    evidence = make_policy_evidence()
    extracted_facts = ExtractedClinicalFacts(
        case_id="case-001",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        conservative_therapy_completed=ClinicalStatus.YES,
        prior_imaging_completed=ClinicalStatus.YES,
        red_flags_present=ClinicalStatus.UNKNOWN,
        contraindications_present=ClinicalStatus.UNKNOWN,
    )
    retrieval_result = RetrievalResult(
        query=PolicySearchQuery(query_text="knee mri", top_k=5),
        hits=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="policy text",
                page_number=1,
            )
        ],
        evidence=[evidence],
    )
    policy_match_result = PolicyMatchResult(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        recommendation_signal=RecommendationSignal.NEEDS_MORE_INFO,
        policy_requirements_summary="Needs conservative therapy.",
        criteria=[
            CoverageCriterion(
                criterion_key="conservative_therapy_completed",
                display_name="Conservative therapy completed",
                status=CriterionStatus.MET,
                rationale="PT documented.",
                policy_evidence=[evidence],
            )
        ],
        unresolved_questions=[],
        cited_evidence=[evidence],
    )
    draft = PriorAuthDraft(
        case_id="case-001",
        review_status=ReviewStatus.NEEDS_REVIEW,
        reviewer_summary="Draft generated.",
        missing_requirements=[],
        unresolved_issues=[],
        risk_flags=[],
    )

    facts_response = ExtractedFactsResponse(
        workflow_id="workflow-001",
        status=WorkflowRunStatus.SUCCEEDED,
        extracted_facts=extracted_facts,
    )
    evidence_response = PolicyEvidenceResponse(
        workflow_id="workflow-001",
        status=WorkflowRunStatus.SUCCEEDED,
        retrieval_result=retrieval_result,
    )
    policy_response = PolicyMatchResponse(
        workflow_id="workflow-001",
        status=WorkflowRunStatus.SUCCEEDED,
        policy_match_result=policy_match_result,
    )
    draft_response = DraftOutputResponse(
        workflow_id="workflow-001",
        status=WorkflowRunStatus.SUCCEEDED,
        prior_auth_draft=draft,
    )

    assert facts_response.extracted_facts.case_id == "case-001"
    assert evidence_response.retrieval_result.evidence[0].evidence_id == "evidence-1"
    assert policy_response.policy_match_result.criteria[0].status == CriterionStatus.MET
    assert draft_response.prior_auth_draft.review_status == ReviewStatus.NEEDS_REVIEW


def test_health_response_defaults_to_ok():
    response = HealthResponse()

    assert response.status == "ok"
    assert response.service == "ai-health-agent-api"
