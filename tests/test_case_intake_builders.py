from case_intake import NormalizedCasePayload, build_patient_case, build_prior_imaging, build_prior_treatments
from domain import ClinicalStatus, ImagingModality, Laterality


def test_build_prior_treatments_maps_completion_and_duration():
    treatments = build_prior_treatments(
        [
            {"treatment_type": "physical_therapy", "completed": "completed", "duration_weeks": 6},
            {"treatment_type": "nsaids", "completed": "no"},
        ]
    )

    assert treatments[0].completed == ClinicalStatus.YES
    assert treatments[0].duration_weeks == 6
    assert treatments[1].completed == ClinicalStatus.NO


def test_build_prior_imaging_maps_domain_enums():
    imaging = build_prior_imaging(
        [
            {
                "modality": "xray",
                "body_region": "knee",
                "laterality": "left",
                "result_summary": "No acute fracture.",
            }
        ]
    )

    assert imaging[0].modality == ImagingModality.XRAY
    assert imaging[0].laterality == Laterality.LEFT


def test_build_patient_case_creates_domain_patient_case():
    payload = NormalizedCasePayload(
        case_id="case-001",
        payer_id="aetna",
        payer_name="Aetna",
        requested_modality="mri",
        requested_body_region="knee",
        requested_laterality="left",
        ordering_specialty="orthopedics",
        raw_clinical_note="Patient has left knee pain for 8 weeks.",
        symptom_duration_weeks=8,
        demographics={"age_years": 45, "sex": "female"},
        prior_treatments=[{"treatment_type": "physical_therapy", "completed": "yes", "duration_weeks": 6}],
        prior_imaging=[{"modality": "xray", "body_region": "knee", "laterality": "left"}],
        structured_intake={"source": "demo"},
    )

    patient_case = build_patient_case(payload)

    assert patient_case.case_id == "case-001"
    assert patient_case.requested_modality == ImagingModality.MRI
    assert patient_case.demographics.age_years == 45
    assert patient_case.prior_treatments[0].completed == ClinicalStatus.YES
    assert patient_case.prior_imaging[0].laterality == Laterality.LEFT
