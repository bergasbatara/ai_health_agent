from rules_engine import (
    check_conservative_therapy_duration,
    check_prior_imaging_consistency,
    check_required_case_fields,
    evaluate_case_rules,
)
from domain import (
    BodyRegion,
    ClinicalStatus,
    ExtractedClinicalFacts,
    ImagingModality,
    Laterality,
    OrderingSpecialty,
    PatientCase,
    PayerId,
)


def make_patient_case(**overrides) -> PatientCase:
    payload = {
        "case_id": "case-001",
        "payer_id": PayerId.AETNA,
        "payer_name": "Aetna",
        "requested_modality": ImagingModality.MRI,
        "requested_body_region": BodyRegion.KNEE,
        "requested_laterality": Laterality.LEFT,
        "ordering_specialty": OrderingSpecialty.ORTHOPEDICS,
        "raw_clinical_note": "Patient has left knee pain for 8 weeks after PT.",
        "symptom_duration_weeks": 8,
        "prior_treatments": [],
        "prior_imaging": [],
    }
    payload.update(overrides)
    return PatientCase(**payload)


def make_extracted_facts(**overrides) -> ExtractedClinicalFacts:
    payload = {
        "case_id": "case-001",
        "requested_modality": ImagingModality.MRI,
        "requested_body_region": BodyRegion.KNEE,
        "requested_laterality": Laterality.LEFT,
        "symptom_duration_weeks": 8,
        "conservative_therapy_completed": ClinicalStatus.UNKNOWN,
        "prior_imaging_completed": ClinicalStatus.UNKNOWN,
        "red_flags_present": ClinicalStatus.NO,
        "contraindications_present": ClinicalStatus.UNKNOWN,
    }
    payload.update(overrides)
    return ExtractedClinicalFacts(**payload)


def test_required_case_fields_pass_for_valid_case():
    check = check_required_case_fields(make_patient_case())

    assert check.passed is True
    assert check.issues == []


def test_conservative_therapy_duration_warns_when_completed_without_duration():
    patient_case = make_patient_case(
        prior_treatments=[{"treatment_type": "physical_therapy", "completed": "yes"}]
    )
    extracted_facts = make_extracted_facts(conservative_therapy_completed=ClinicalStatus.YES)

    check = check_conservative_therapy_duration(patient_case, extracted_facts)

    assert check.passed is True
    assert check.issues[0].code == "missing_conservative_therapy_duration"


def test_prior_imaging_consistency_warns_when_missing_record():
    patient_case = make_patient_case(prior_imaging=[])
    extracted_facts = make_extracted_facts(prior_imaging_completed=ClinicalStatus.YES)

    check = check_prior_imaging_consistency(patient_case, extracted_facts)

    assert check.passed is True
    assert check.issues[0].code == "prior_imaging_claim_without_record"


def test_evaluate_case_rules_aggregates_checks():
    patient_case = make_patient_case(
        prior_treatments=[{"treatment_type": "physical_therapy", "completed": "yes"}]
    )
    extracted_facts = make_extracted_facts(
        conservative_therapy_completed=ClinicalStatus.YES,
        prior_imaging_completed=ClinicalStatus.YES,
    )

    result = evaluate_case_rules(patient_case, extracted_facts)

    assert len(result.checks) == 3
    assert len(result.issues) >= 2
