from pathlib import Path

from data_ingestion.models import EmbeddedChunk, PolicyChunk
from orchestration import (
    CrewAIAdapterError,
    CrewAIOrchestrationAdapter,
    CrewAIResponseProvider,
    WorkflowRunStatus,
    is_crewai_available,
    run_prior_auth_workflow_with_crewai,
)
from retrieval import InMemoryVectorSearcher


class FakeCrewOutput:
    def __init__(self, raw: str):
        self.raw = raw


class FakeCrew:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def kickoff(self, inputs=None):
        self.calls.append(dict(inputs or {}))
        if not self.responses:
            return None
        return FakeCrewOutput(self.responses.pop(0))


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


def test_crewai_response_provider_passes_prompts_into_kickoff():
    crew = FakeCrew(['{"ok": true}'])
    provider = CrewAIResponseProvider(crew, static_inputs={"role": "extractor"})

    output = provider.generate(system_prompt="system text", user_prompt="user text")

    assert output == '{"ok": true}'
    assert crew.calls[0]["role"] == "extractor"
    assert crew.calls[0]["system_prompt"] == "system text"
    assert crew.calls[0]["user_prompt"] == "user text"


def test_crewai_response_provider_raises_on_empty_output():
    crew = FakeCrew([])
    provider = CrewAIResponseProvider(crew)

    try:
        provider.generate(system_prompt="system", user_prompt="user")
    except CrewAIAdapterError as exc:
        assert "returned no output" in str(exc)
    else:
        raise AssertionError("Expected CrewAIAdapterError for missing crew output")


def test_crewai_adapter_runs_full_workflow(tmp_path: Path):
    adapter = CrewAIOrchestrationAdapter()
    result = adapter.run_with_crews(
        workflow_id="workflow-001",
        case_path=make_case_file(tmp_path),
        retrieval_searcher=make_searcher(),
        extractor_crew=FakeCrew([valid_extractor_output()]),
        policy_matcher_crew=FakeCrew([valid_policy_matcher_output()]),
        form_filler_crew=FakeCrew([valid_form_filler_output()]),
    )

    assert result.status == WorkflowRunStatus.SUCCEEDED
    assert result.artifacts.rules_result is not None


def test_run_prior_auth_workflow_with_crewai_function(tmp_path: Path):
    result = run_prior_auth_workflow_with_crewai(
        workflow_id="workflow-002",
        case_path=make_case_file(tmp_path),
        retrieval_searcher=make_searcher(),
        extractor_crew=FakeCrew([valid_extractor_output()]),
        policy_matcher_crew=FakeCrew([valid_policy_matcher_output()]),
        form_filler_crew=FakeCrew([valid_form_filler_output()]),
    )

    assert result.status == WorkflowRunStatus.SUCCEEDED
    assert len(result.step_history) == 6


def test_is_crewai_available_returns_boolean():
    assert isinstance(is_crewai_available(), bool)
