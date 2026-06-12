from case_intake import (
    NormalizedCasePayload,
    StructuredCasePayload,
    TextCasePayload,
    normalize_body_region,
    normalize_case_payload,
    normalize_laterality,
    normalize_modality,
    normalize_payer_id,
)
from domain import BodyRegion, ImagingModality, Laterality, PayerId


def test_basic_value_normalizers_map_common_inputs():
    assert normalize_payer_id("Aetna") == PayerId.AETNA
    assert normalize_modality("MRI of left knee") == ImagingModality.MRI
    assert normalize_body_region("left knee pain") == BodyRegion.KNEE
    assert normalize_laterality("left knee") == Laterality.LEFT


def test_normalize_structured_case_payload_returns_canonical_shape():
    payload = StructuredCasePayload(
        case_id="case-001",
        payer="Aetna",
        requested_modality="MRI",
        requested_body_region="knee",
        requested_laterality="left",
        ordering_specialty="Orthopedics",
        raw_clinical_note="Patient has left knee pain for 8 weeks.",
        symptom_duration_weeks=8,
        additional_fields={"source": "demo"},
    )

    normalized = normalize_case_payload(payload)

    assert isinstance(normalized, NormalizedCasePayload)
    assert normalized.payer_id == "aetna"
    assert normalized.requested_modality == "mri"
    assert normalized.requested_body_region == "knee"
    assert normalized.requested_laterality == "left"


def test_normalize_text_case_payload_uses_metadata_and_note_fallbacks():
    payload = TextCasePayload(
        metadata={
            "case_id": "case-002",
            "payer": "Cigna",
            "requested_modality": "MRI",
            "ordering_specialty": "primary care",
        },
        raw_clinical_note="Patient has right knee pain after PT.",
    )

    normalized = normalize_case_payload(payload)

    assert normalized.case_id == "case-002"
    assert normalized.payer_id == "cigna"
    assert normalized.requested_body_region == "knee"
    assert normalized.requested_laterality == "right"
    assert normalized.ordering_specialty == "primary_care"


def test_normalize_unknown_values_falls_back_safely():
    payload = StructuredCasePayload(
        case_id="case-003",
        payer="Unknown Plan",
        raw_clinical_note="General pain.",
    )

    normalized = normalize_case_payload(payload)

    assert normalized.payer_id == "other"
    assert normalized.requested_modality == "other"
    assert normalized.requested_body_region == "other"
    assert normalized.requested_laterality == "unknown"
