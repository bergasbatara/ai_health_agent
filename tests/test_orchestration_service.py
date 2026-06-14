from pathlib import Path

from agents import StaticResponseProvider
from data_ingestion.models import EmbeddedChunk, PolicyChunk
from orchestration import (
    OrchestrationService,
    OrchestrationServiceConfig,
    RetryPolicy,
    WorkflowRunStatus,
    WorkflowStep,
    run_prior_auth_workflow,
)
from retrieval import InMemoryVectorSearcher


def make_case_file(tmp_path: Path) -> str:
    case_path = tmp_path / "case-001.json"
    case_path.write_text(
        """
        {
          "case_id": "case-001",
          "payer": "Aetna",
          "requested_modality": "MRI",
          "requested_body_region": "knee",
          "requested_laterality": "left",
          "ordering_specialty": "orthopedics",
          "raw_clinical_note": "Patient has left knee pain for 8 weeks after PT.",
          "prior_treatments": [
            {"treatment_type": "physical_therapy", "completed": "yes", "duration_weeks": 6}
          ],
          "prior_imaging": [
            {"modality": "xray", "body_region": "knee", "laterality": "left", "result_summary": "No acute fracture."}
          ]
        }
        """.strip(),
        encoding="utf-8",
    )
    return str(case_path)


def make_searcher() -> InMemoryVectorSearcher:
    return InMemoryVectorSearcher(
        [
            EmbeddedChunk(
                chunk=PolicyChunk(
                    chunk_id="chunk-1",
                    document_id="aetna-knee-mri-policy",
                    page_number=1,
                    chunk_index=0,
                    text="Patient must complete conservative therapy before MRI approval.",
                    section_label="Criteria",
                    study_family="knee_mri",
                    retrieval_metadata={
                        "payer_id": "aetna",
                        "requested_modality": "mri",
                        "requested_body_region": "knee",
                        "study_family": "knee_mri",
                    },
                ),
                embedding=[0.1, 0.2, 0.3],
            )
        ]
    )


def valid_extractor_output() -> str:
    return """
    {
      "extracted_facts": {
        "case_id": "case-001",
        "requested_modality": "mri",
        "requested_body_region": "knee",
        "requested_laterality": "left",
        "symptom_duration_weeks": 8,
        "conservative_therapy_completed": "yes",
        "prior_imaging_completed": "yes",
        "red_flags_present": "no",
        "contraindications_present": "unknown"
      },
      "reasoning_summary": "Structured facts extracted from the note."
    }
    """


def valid_policy_matcher_output() -> str:
    return """
    {
      "policy_match_result": {
        "case_id": "case-001",
        "payer_id": "aetna",
        "payer_name": "Aetna",
        "requested_modality": "mri",
        "requested_body_region": "knee",
        "requested_laterality": "left",
        "recommendation_signal": "needs_more_info",
        "policy_requirements_summary": "Knee MRI requires conservative treatment.",
        "criteria": [
          {
            "criterion_key": "conservative_therapy_completed",
            "display_name": "Conservative therapy completed",
            "status": "met",
            "rationale": "PT documented for 6 weeks.",
            "policy_evidence": [
              {
                "evidence_id": "evidence-1",
                "document_id": "aetna-knee-mri-policy",
                "chunk_id": "chunk-1",
                "citation_text": "MRI requires six weeks of conservative therapy.",
                "relevance_score": 0.91,
                "page_number": 2
              }
            ]
          }
        ],
        "unresolved_questions": [],
        "cited_evidence": [
          {
            "evidence_id": "evidence-1",
            "document_id": "aetna-knee-mri-policy",
            "chunk_id": "chunk-1",
            "citation_text": "MRI requires six weeks of conservative therapy.",
            "relevance_score": 0.91,
            "page_number": 2
          }
        ]
      },
      "reasoning_summary": "Policy criteria mapped from retrieved evidence."
    }
    """


def valid_form_filler_output() -> str:
    return """
    {
      "prior_auth_draft": {
        "case_id": "case-001",
        "review_status": "needs_review",
        "reviewer_summary": "Draft generated for review.",
        "form_fields": [
          {
            "field_name": "requested_study",
            "field_value": "Left knee MRI"
          }
        ],
        "missing_requirements": [],
        "unresolved_issues": [],
        "risk_flags": []
      },
      "reasoning_summary": "Draft fields populated from case and policy match."
    }
    """


def test_orchestration_service_runs_workflow(tmp_path: Path):
    service = OrchestrationService(
        config=OrchestrationServiceConfig(
            retry_policy=RetryPolicy(
                max_attempts=2,
                retryable_steps=[WorkflowStep.FACT_EXTRACTION],
            )
        )
    )

    result = service.run_prior_auth_workflow(
        workflow_id="workflow-001",
        case_path=make_case_file(tmp_path),
        retrieval_searcher=make_searcher(),
        extractor_provider=StaticResponseProvider([valid_extractor_output()]),
        policy_matcher_provider=StaticResponseProvider([valid_policy_matcher_output()]),
        form_filler_provider=StaticResponseProvider([valid_form_filler_output()]),
    )

    assert result.status == WorkflowRunStatus.SUCCEEDED
    assert result.artifacts.patient_case is not None
    assert result.artifacts.prior_auth_draft is not None


def test_run_prior_auth_workflow_function_uses_service_defaults(tmp_path: Path):
    result = run_prior_auth_workflow(
        workflow_id="workflow-002",
        case_path=make_case_file(tmp_path),
        retrieval_searcher=make_searcher(),
        extractor_provider=StaticResponseProvider([valid_extractor_output()]),
        policy_matcher_provider=StaticResponseProvider([valid_policy_matcher_output()]),
        form_filler_provider=StaticResponseProvider([valid_form_filler_output()]),
    )

    assert result.status == WorkflowRunStatus.SUCCEEDED
    assert len(result.step_history) == 6
