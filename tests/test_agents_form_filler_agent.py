import pytest

from agents import FormFillerInput, StaticResponseProvider, run_form_filler_agent
from agents.runtime import AgentRuntimeError
from domain import (
    BodyRegion,
    ClinicalStatus,
    CoverageCriterion,
    CriterionStatus,
    DraftFormField,
    ExtractedClinicalFacts,
    ImagingModality,
    Laterality,
    OrderingSpecialty,
    PatientCase,
    PayerId,
    PolicyEvidence,
    PolicyMatchResult,
    ReviewStatus,
)


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
    )


def make_extracted_facts() -> ExtractedClinicalFacts:
    return ExtractedClinicalFacts(
        case_id="case-001",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        symptom_duration_weeks=8,
        conservative_therapy_completed=ClinicalStatus.YES,
        prior_imaging_completed=ClinicalStatus.NO,
        red_flags_present=ClinicalStatus.NO,
        contraindications_present=ClinicalStatus.UNKNOWN,
    )


def make_policy_match_result() -> PolicyMatchResult:
    evidence = PolicyEvidence(
        evidence_id="evidence-1",
        document_id="aetna-knee-mri-policy",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
        section_label="Knee Mri Criteria",
        relevance_score=0.91,
        page_number=2,
    )
    return PolicyMatchResult(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
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
        cited_evidence=[evidence],
    )


def valid_form_filler_output() -> str:
    return """
    {
      "prior_auth_draft": {
        "case_id": "case-001",
        "review_status": "needs_review",
        "reviewer_summary": "Draft generated for orthopedic review.",
        "form_fields": [
          {
            "field_name": "requested_study",
            "field_value": "Left knee MRI",
            "source": "patient_case"
          }
        ],
        "missing_requirements": [],
        "unresolved_issues": [],
        "risk_flags": [],
        "submission_notes": "Conservative therapy documented."
      },
      "reasoning_summary": "Draft assembled from case facts and policy findings."
    }
    """


def test_run_form_filler_agent_returns_typed_output():
    agent_input = FormFillerInput(
        patient_case=make_patient_case(),
        extracted_facts=make_extracted_facts(),
        policy_match_result=make_policy_match_result(),
    )
    provider = StaticResponseProvider(responses=[valid_form_filler_output()])

    output = run_form_filler_agent(agent_input, provider=provider)

    assert output.prior_auth_draft.case_id == "case-001"
    assert output.prior_auth_draft.review_status == ReviewStatus.NEEDS_REVIEW
    assert output.prior_auth_draft.form_fields[0].field_name == "requested_study"


def test_run_form_filler_agent_raises_on_invalid_output():
    agent_input = FormFillerInput(
        patient_case=make_patient_case(),
        extracted_facts=make_extracted_facts(),
        policy_match_result=make_policy_match_result(),
    )
    provider = StaticResponseProvider(responses=["{bad-json}"])

    with pytest.raises(AgentRuntimeError):
        run_form_filler_agent(agent_input, provider=provider, max_retries=0)
