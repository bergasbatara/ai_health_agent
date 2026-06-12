from domain import (
    BodyRegion,
    ImagingModality,
    Laterality,
    OrderingSpecialty,
    PatientCase,
    PayerId,
)
from retrieval import build_policy_search_query, build_query_filters, build_query_text, infer_study_family


def make_patient_case(**overrides) -> PatientCase:
    payload = {
        "case_id": "case-001",
        "payer_id": PayerId.AETNA,
        "payer_name": "Aetna",
        "requested_modality": ImagingModality.MRI,
        "requested_body_region": BodyRegion.KNEE,
        "requested_laterality": Laterality.LEFT,
        "ordering_specialty": OrderingSpecialty.ORTHOPEDICS,
        "raw_clinical_note": "Patient has left knee pain for 8 weeks after physical therapy.",
        "reason_for_order": "Persistent knee pain",
        "diagnosis": "Internal derangement",
        "symptom_duration_weeks": 8,
        "prior_treatments": [],
        "prior_imaging": [],
    }
    payload.update(overrides)
    return PatientCase(**payload)


def test_build_query_text_includes_core_case_signals():
    patient_case = make_patient_case(prior_treatments=[{"treatment_type": "physical_therapy"}])

    query_text = build_query_text(patient_case)

    assert "Aetna" in query_text
    assert "knee" in query_text
    assert "mri" in query_text
    assert "conservative therapy" in query_text


def test_infer_study_family_for_knee_mri():
    patient_case = make_patient_case()

    assert infer_study_family(patient_case) == "knee_mri"


def test_build_query_filters_returns_expected_metadata_filters():
    patient_case = make_patient_case()

    filters = build_query_filters(patient_case, "knee_mri")

    assert filters == {
        "payer_id": "aetna",
        "requested_modality": "mri",
        "requested_body_region": "knee",
        "study_family": "knee_mri",
    }


def test_build_policy_search_query_returns_complete_query_model():
    patient_case = make_patient_case(prior_imaging=[{"modality": "xray", "body_region": "knee"}])

    query = build_policy_search_query(patient_case, top_k=3)

    assert query.payer_id == "aetna"
    assert query.study_family == "knee_mri"
    assert query.top_k == 3
    assert query.filters["study_family"] == "knee_mri"
