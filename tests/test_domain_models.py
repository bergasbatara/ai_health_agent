import pytest
from pydantic import ValidationError

from domain import (
    BodyRegion,
    ClinicalFact,
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
    PriorImagingStudy,
    PriorTreatment,
    ReviewStatus,
)


def make_patient_case(**overrides):
    payload = {
        "case_id": "case-001",
        "payer_id": PayerId.AETNA,
        "payer_name": "Aetna",
        "requested_modality": ImagingModality.MRI,
        "requested_body_region": BodyRegion.KNEE,
        "requested_laterality": Laterality.LEFT,
        "ordering_specialty": OrderingSpecialty.ORTHOPEDICS,
        "raw_clinical_note": "Patient has left knee pain for 8 weeks after PT failed.",
        "symptom_duration_weeks": 8,
        "prior_treatments": [
            {
                "treatment_type": "physical_therapy",
                "completed": ClinicalStatus.YES,
                "duration_weeks": 6,
            }
        ],
        "prior_imaging": [
            {
                "modality": ImagingModality.XRAY,
                "body_region": BodyRegion.KNEE,
                "laterality": Laterality.LEFT,
                "result_summary": "No acute fracture.",
            }
        ],
    }
    payload.update(overrides)
    return PatientCase(**payload)


def make_policy_evidence(document_id: str, evidence_id: str, chunk_id: str) -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id=evidence_id,
        document_id=document_id,
        chunk_id=chunk_id,
        citation_text="MRI requires 6 weeks of provider-directed conservative care.",
        section_label="Knee MRI Criteria",
        relevance_score=0.92,
        page_number=4,
    )


def test_patient_case_allows_partial_structured_data_and_raw_note():
    patient_case = make_patient_case(reason_for_order="Persistent knee pain")

    assert patient_case.raw_clinical_note.startswith("Patient has left knee pain")
    assert patient_case.reason_for_order == "Persistent knee pain"
    assert patient_case.prior_treatments[0].duration_weeks == 6


def test_patient_case_rejects_missing_requested_study_fields():
    with pytest.raises(ValidationError):
        make_patient_case(requested_modality=None)


def test_extracted_facts_preserve_unknown_symptom_duration():
    extracted = ExtractedClinicalFacts(
        case_id="case-001",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.RIGHT,
        symptom_duration_weeks=None,
        conservative_therapy_completed=ClinicalStatus.UNKNOWN,
        prior_imaging_completed=ClinicalStatus.NO,
        red_flags_present=ClinicalStatus.NO,
        contraindications_present=ClinicalStatus.UNKNOWN,
    )

    assert extracted.symptom_duration_status == ClinicalStatus.UNKNOWN
    assert extracted.requested_laterality == Laterality.RIGHT


def test_criteria_support_multiple_citations():
    criterion = CoverageCriterion(
        criterion_key="conservative_therapy_completed",
        display_name="Conservative therapy completed",
        status=CriterionStatus.MET,
        rationale="The case documents 6 weeks of PT and policy requires 6 weeks.",
        policy_evidence=[
            make_policy_evidence("aetna-knee-mri", "ev-1", "chunk-1"),
            make_policy_evidence("cigna-msk-2025", "ev-2", "chunk-4"),
        ],
        patient_supporting_facts=[
            ClinicalFact(
                fact_key="physical_therapy_duration_weeks",
                value="6",
                confidence=0.98,
            )
        ],
    )

    assert criterion.status == CriterionStatus.MET
    assert len(criterion.policy_evidence) == 2


def test_prior_auth_draft_always_has_review_status_and_unresolved_issue_container():
    draft = PriorAuthDraft(
        case_id="case-001",
        reviewer_summary="Draft generated for orthopedic review.",
    )

    assert draft.review_status == ReviewStatus.DRAFT
    assert draft.unresolved_issues == []


def test_cross_payer_policy_match_result_supports_same_criterion_shape():
    criterion = CoverageCriterion(
        criterion_key="prior_imaging_done",
        display_name="Prior imaging completed",
        status=CriterionStatus.MET,
        rationale="X-ray was completed before MRI request.",
        policy_evidence=[
            make_policy_evidence("medadv-rad-2026", "ev-3", "chunk-7"),
        ],
    )

    aetna_result = PolicyMatchResult(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        policy_requirements_summary="Knee MRI requires conservative treatment and prior imaging.",
        criteria=[criterion],
        cited_evidence=criterion.policy_evidence,
    )
    cigna_result = PolicyMatchResult(
        case_id="case-001",
        payer_id=PayerId.CIGNA,
        payer_name="Cigna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        policy_requirements_summary="Knee MRI requires conservative treatment and prior imaging.",
        criteria=[criterion.model_copy()],
        cited_evidence=criterion.policy_evidence,
    )

    assert aetna_result.criteria[0].criterion_key == cigna_result.criteria[0].criterion_key
    assert aetna_result.payer_id != cigna_result.payer_id


def test_prior_imaging_and_treatment_models_validate():
    case = make_patient_case(
        prior_treatments=[PriorTreatment(treatment_type="nsaids", completed=ClinicalStatus.YES)],
        prior_imaging=[
            PriorImagingStudy(
                modality=ImagingModality.XRAY,
                body_region=BodyRegion.KNEE,
                laterality=Laterality.LEFT,
            )
        ],
    )

    assert case.prior_treatments[0].treatment_type == "nsaids"
    assert case.prior_imaging[0].modality == ImagingModality.XRAY
