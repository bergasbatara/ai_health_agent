from pathlib import Path

from agents import StaticResponseProvider
from data_ingestion.models import EmbeddedChunk, PolicyChunk
from orchestration import RetryPolicy, WorkflowRunInputs, WorkflowRunStatus, WorkflowStep, run_workflow
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


def valid_policy_matcher_output_met() -> str:
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


def valid_policy_matcher_output_not_met() -> str:
    return """
    {
      "policy_match_result": {
        "case_id": "case-001",
        "payer_id": "aetna",
        "payer_name": "Aetna",
        "requested_modality": "mri",
        "requested_body_region": "knee",
        "requested_laterality": "left",
        "recommendation_signal": "likely_deny",
        "policy_requirements_summary": "Knee MRI requires conservative treatment.",
        "criteria": [
          {
            "criterion_key": "conservative_therapy_completed",
            "display_name": "Conservative therapy completed",
            "status": "not_met",
            "rationale": "PT not documented.",
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


def valid_form_filler_output_needs_review() -> str:
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


def valid_form_filler_output_ready() -> str:
    return """
    {
      "prior_auth_draft": {
        "case_id": "case-001",
        "review_status": "ready_for_submission",
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


def test_run_workflow_returns_succeeded_result(tmp_path: Path):
    result = run_workflow(
        "workflow-001",
        WorkflowRunInputs(
            case_path=make_case_file(tmp_path),
            retrieval_searcher=make_searcher(),
            extractor_provider=StaticResponseProvider([valid_extractor_output()]),
            policy_matcher_provider=StaticResponseProvider([valid_policy_matcher_output_met()]),
            form_filler_provider=StaticResponseProvider([valid_form_filler_output_needs_review()]),
        ),
    )

    assert result.status == WorkflowRunStatus.SUCCEEDED
    assert result.artifacts.patient_case is not None
    assert result.artifacts.rules_result is not None
    assert len(result.step_history) == 6
    assert result.failures == []


def test_run_workflow_retries_retryable_step_and_then_succeeds(tmp_path: Path):
    result = run_workflow(
        "workflow-002",
        WorkflowRunInputs(
            case_path=make_case_file(tmp_path),
            retrieval_searcher=make_searcher(),
            extractor_provider=StaticResponseProvider(["{bad-json}", valid_extractor_output()]),
            policy_matcher_provider=StaticResponseProvider([valid_policy_matcher_output_met()]),
            form_filler_provider=StaticResponseProvider([valid_form_filler_output_needs_review()]),
            agent_max_retries_per_call=0,
        ),
        retry_policy=RetryPolicy(
            max_attempts=2,
            retryable_steps=[WorkflowStep.FACT_EXTRACTION],
        ),
    )

    fact_extraction_records = [record for record in result.step_history if record.step == WorkflowStep.FACT_EXTRACTION]

    assert result.status == WorkflowRunStatus.SUCCEEDED
    assert len(fact_extraction_records) == 2
    assert fact_extraction_records[0].status == "failed"
    assert fact_extraction_records[1].status == "succeeded"


def test_run_workflow_returns_human_review_when_rules_block_submission(tmp_path: Path):
    result = run_workflow(
        "workflow-003",
        WorkflowRunInputs(
            case_path=make_case_file(tmp_path),
            retrieval_searcher=make_searcher(),
            extractor_provider=StaticResponseProvider([valid_extractor_output()]),
            policy_matcher_provider=StaticResponseProvider([valid_policy_matcher_output_not_met()]),
            form_filler_provider=StaticResponseProvider([valid_form_filler_output_ready()]),
        ),
    )

    assert result.status == WorkflowRunStatus.NEEDS_HUMAN_REVIEW
    assert result.artifacts.rules_result is not None
    assert result.artifacts.rules_result.passed is False
    assert result.failures[-1].disposition == "human_review"
