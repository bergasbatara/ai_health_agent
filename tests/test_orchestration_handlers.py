from pathlib import Path

from agents import StaticResponseProvider
from data_ingestion.models import EmbeddedChunk, PolicyChunk
from domain import (
    BodyRegion,
    ClinicalStatus,
    CoverageCriterion,
    CriterionStatus,
    ExtractedClinicalFacts,
    ImagingModality,
    Laterality,
    OrderingSpecialty,
    PatientCase,
    PayerId,
    PolicyEvidence,
    PolicyMatchResult,
    PriorAuthDraft,
    RecommendationSignal,
    ReviewStatus,
)
from orchestration import (
    WorkflowArtifactBundle,
    handle_case_intake,
    handle_draft_generation,
    handle_fact_extraction,
    handle_policy_matching,
    handle_policy_retrieval,
    handle_rules_validation,
)
from retrieval import InMemoryVectorSearcher


def make_patient_case() -> PatientCase:
    return PatientCase(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        ordering_specialty=OrderingSpecialty.ORTHOPEDICS,
        raw_clinical_note="Patient has left knee pain for 8 weeks after PT.",
        reason_for_order="Persistent knee pain",
        symptom_duration_weeks=8,
        prior_treatments=[{"treatment_type": "physical_therapy", "completed": "yes", "duration_weeks": 6}],
        prior_imaging=[
            {
                "modality": "xray",
                "body_region": "knee",
                "laterality": "left",
                "result_summary": "No acute fracture.",
            }
        ],
    )


def make_extracted_facts() -> ExtractedClinicalFacts:
    return ExtractedClinicalFacts(
        case_id="case-001",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        symptom_duration_weeks=8,
        conservative_therapy_completed=ClinicalStatus.YES,
        prior_imaging_completed=ClinicalStatus.YES,
        red_flags_present=ClinicalStatus.NO,
        contraindications_present=ClinicalStatus.UNKNOWN,
    )


def make_policy_evidence() -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id="evidence-1",
        document_id="aetna-knee-mri-policy",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
        relevance_score=0.91,
        page_number=2,
    )


def make_policy_match_result() -> PolicyMatchResult:
    evidence = make_policy_evidence()
    return PolicyMatchResult(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        recommendation_signal=RecommendationSignal.NEEDS_MORE_INFO,
        policy_requirements_summary="Knee MRI requires conservative treatment.",
        criteria=[
            CoverageCriterion(
                criterion_key="conservative_therapy_completed",
                display_name="Conservative therapy completed",
                status=CriterionStatus.MET,
                rationale="PT documented for 6 weeks.",
                policy_evidence=[evidence],
            )
        ],
        unresolved_questions=[],
        cited_evidence=[evidence],
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


def make_embedded_chunk() -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk=PolicyChunk(
            chunk_id="chunk-1",
            document_id="aetna-knee-mri-policy",
            page_number=1,
            chunk_index=0,
            text="Patient must complete conservative therapy before MRI approval.",
            section_label="Knee MRI Criteria",
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


def test_handle_case_intake_returns_raw_file_and_patient_case(tmp_path: Path):
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
          "raw_clinical_note": "Patient has left knee pain for 8 weeks after PT."
        }
        """.strip(),
        encoding="utf-8",
    )

    bundle = handle_case_intake(str(case_path))

    assert isinstance(bundle, WorkflowArtifactBundle)
    assert bundle.raw_case_file is not None
    assert bundle.patient_case is not None
    assert bundle.patient_case.case_id == "case-001"


def test_handle_fact_extraction_returns_extractor_artifacts():
    bundle = handle_fact_extraction(
        make_patient_case(),
        provider=StaticResponseProvider(responses=[valid_extractor_output()]),
    )

    assert bundle.extractor_output is not None
    assert bundle.extracted_facts is not None
    assert bundle.extracted_facts.conservative_therapy_completed == ClinicalStatus.YES


def test_handle_policy_retrieval_returns_retrieval_result():
    bundle = handle_policy_retrieval(
        make_patient_case(),
        searcher=InMemoryVectorSearcher([make_embedded_chunk()]),
    )

    assert bundle.retrieval_result is not None
    assert len(bundle.retrieval_result.evidence) == 1


def test_handle_policy_matching_returns_policy_match_artifacts():
    bundle = handle_policy_matching(
        make_patient_case(),
        make_extracted_facts(),
        [make_policy_evidence()],
        provider=StaticResponseProvider(responses=[valid_policy_matcher_output()]),
    )

    assert bundle.policy_matcher_output is not None
    assert bundle.policy_match_result is not None
    assert bundle.policy_match_result.cited_evidence[0].document_id == "aetna-knee-mri-policy"


def test_handle_draft_generation_returns_draft_artifacts():
    bundle = handle_draft_generation(
        make_patient_case(),
        make_extracted_facts(),
        make_policy_match_result(),
        provider=StaticResponseProvider(responses=[valid_form_filler_output()]),
    )

    assert bundle.form_filler_output is not None
    assert bundle.prior_auth_draft is not None
    assert bundle.prior_auth_draft.review_status == ReviewStatus.NEEDS_REVIEW


def test_handle_rules_validation_returns_rules_result():
    bundle = handle_rules_validation(
        make_patient_case(),
        make_extracted_facts(),
        make_policy_match_result(),
        PriorAuthDraft(
            case_id="case-001",
            review_status=ReviewStatus.NEEDS_REVIEW,
            reviewer_summary="Draft generated for review.",
            missing_requirements=[],
            unresolved_issues=[],
            risk_flags=[],
        ),
    )

    assert bundle.rules_result is not None
    assert bundle.rules_result.passed is True
