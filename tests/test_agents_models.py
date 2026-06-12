import pytest
from pydantic import ValidationError

from agents import (
    ExtractorInput,
    ExtractorOutput,
    FormFillerInput,
    FormFillerOutput,
    PolicyMatcherInput,
    PolicyMatcherOutput,
)
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


def make_policy_evidence() -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id="evidence-1",
        document_id="aetna-knee-mri-policy",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
        section_label="Knee Mri Criteria",
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


def test_extractor_models_wrap_patient_case_and_facts():
    extractor_input = ExtractorInput(patient_case=make_patient_case())
    extractor_output = ExtractorOutput(extracted_facts=make_extracted_facts(), reasoning_summary="Facts extracted.")

    assert extractor_input.patient_case.case_id == "case-001"
    assert extractor_output.extracted_facts.conservative_therapy_completed == ClinicalStatus.YES


def test_policy_matcher_models_wrap_evidence_and_results():
    matcher_input = PolicyMatcherInput(
        patient_case=make_patient_case(),
        extracted_facts=make_extracted_facts(),
        policy_evidence=[make_policy_evidence()],
    )
    matcher_output = PolicyMatcherOutput(
        policy_match_result=make_policy_match_result(),
        reasoning_summary="Policy evidence supports approval readiness.",
    )

    assert len(matcher_input.policy_evidence) == 1
    assert matcher_output.policy_match_result.cited_evidence[0].evidence_id == "evidence-1"


def test_policy_matcher_output_requires_cited_evidence():
    with pytest.raises(ValidationError):
        PolicyMatcherOutput(
            policy_match_result=PolicyMatchResult(
                case_id="case-001",
                payer_id=PayerId.AETNA,
                payer_name="Aetna",
                requested_modality=ImagingModality.MRI,
                requested_body_region=BodyRegion.KNEE,
                policy_requirements_summary="Summary without evidence.",
            )
        )


def test_form_filler_models_wrap_prior_auth_draft():
    draft = PriorAuthDraft(
        case_id="case-001",
        review_status=ReviewStatus.NEEDS_REVIEW,
        reviewer_summary="Draft generated for review.",
    )
    filler_input = FormFillerInput(
        patient_case=make_patient_case(),
        extracted_facts=make_extracted_facts(),
        policy_match_result=make_policy_match_result(),
    )
    filler_output = FormFillerOutput(prior_auth_draft=draft, reasoning_summary="Draft assembled.")

    assert filler_input.policy_match_result.case_id == "case-001"
    assert filler_output.prior_auth_draft.review_status == ReviewStatus.NEEDS_REVIEW
