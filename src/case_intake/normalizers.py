from __future__ import annotations

import re

from domain import BodyRegion, ImagingModality, Laterality, OrderingSpecialty, PayerId

from .models import NormalizedCasePayload, StructuredCasePayload, TextCasePayload


PAYER_ALIASES = {
    "aetna": PayerId.AETNA,
    "cigna": PayerId.CIGNA,
    "medadv": PayerId.MEDADV,
}

MODALITY_ALIASES = {
    "mri": ImagingModality.MRI,
    "magnetic resonance imaging": ImagingModality.MRI,
    "ct": ImagingModality.CT,
    "cat scan": ImagingModality.CT,
    "xray": ImagingModality.XRAY,
    "x-ray": ImagingModality.XRAY,
    "ultrasound": ImagingModality.ULTRASOUND,
    "pet": ImagingModality.PET,
}

BODY_REGION_ALIASES = {
    "knee": BodyRegion.KNEE,
    "lumbar spine": BodyRegion.LUMBAR_SPINE,
    "lumbar_spine": BodyRegion.LUMBAR_SPINE,
    "lower back": BodyRegion.LUMBAR_SPINE,
    "thoracic spine": BodyRegion.THORACIC_SPINE,
    "thoracic_spine": BodyRegion.THORACIC_SPINE,
    "cervical spine": BodyRegion.CERVICAL_SPINE,
    "cervical_spine": BodyRegion.CERVICAL_SPINE,
    "neck": BodyRegion.CERVICAL_SPINE,
    "shoulder": BodyRegion.SHOULDER,
    "hip": BodyRegion.HIP,
    "abdomen": BodyRegion.ABDOMEN,
    "pelvis": BodyRegion.PELVIS,
    "head": BodyRegion.HEAD,
    "chest": BodyRegion.CHEST,
}

LATERALITY_ALIASES = {
    "left": Laterality.LEFT,
    "right": Laterality.RIGHT,
    "bilateral": Laterality.BILATERAL,
    "both": Laterality.BILATERAL,
    "midline": Laterality.MIDLINE,
    "not applicable": Laterality.NOT_APPLICABLE,
    "not_applicable": Laterality.NOT_APPLICABLE,
    "na": Laterality.NOT_APPLICABLE,
    "n/a": Laterality.NOT_APPLICABLE,
}

SPECIALTY_ALIASES = {
    "primary care": OrderingSpecialty.PRIMARY_CARE,
    "pcp": OrderingSpecialty.PRIMARY_CARE,
    "orthopedics": OrderingSpecialty.ORTHOPEDICS,
    "orthopedic surgery": OrderingSpecialty.ORTHOPEDICS,
    "sports medicine": OrderingSpecialty.SPORTS_MEDICINE,
    "physical medicine": OrderingSpecialty.PHYSICAL_MEDICINE,
    "pm&r": OrderingSpecialty.PHYSICAL_MEDICINE,
    "emergency medicine": OrderingSpecialty.EMERGENCY_MEDICINE,
}


def _normalize_token(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def normalize_payer_id(payer: str | None = None, payer_id: str | None = None) -> PayerId:
    for candidate in (payer_id, payer):
        normalized = _normalize_token(candidate)
        if normalized in PAYER_ALIASES:
            return PAYER_ALIASES[normalized]
    return PayerId.OTHER


def normalize_payer_name(payer: str | None, normalized_payer_id: PayerId) -> str:
    if payer and payer.strip():
        return payer.strip()
    if normalized_payer_id == PayerId.AETNA:
        return "Aetna"
    if normalized_payer_id == PayerId.CIGNA:
        return "Cigna"
    if normalized_payer_id == PayerId.MEDADV:
        return "MedAdv"
    return "Other"


def normalize_modality(value: str | None, fallback_text: str | None = None) -> ImagingModality:
    for candidate in (value, fallback_text):
        normalized = _normalize_token(candidate)
        if normalized in MODALITY_ALIASES:
            return MODALITY_ALIASES[normalized]
        if "mri" in normalized:
            return ImagingModality.MRI
        if "ct" in normalized:
            return ImagingModality.CT
    return ImagingModality.OTHER


def normalize_body_region(value: str | None, fallback_text: str | None = None) -> BodyRegion:
    for candidate in (value, fallback_text):
        normalized = _normalize_token(candidate)
        if normalized in BODY_REGION_ALIASES:
            return BODY_REGION_ALIASES[normalized]
        for token, region in BODY_REGION_ALIASES.items():
            if token in normalized:
                return region
    return BodyRegion.OTHER


def normalize_laterality(value: str | None, fallback_text: str | None = None) -> Laterality:
    for candidate in (value, fallback_text):
        normalized = _normalize_token(candidate)
        if normalized in LATERALITY_ALIASES:
            return LATERALITY_ALIASES[normalized]
        if "left" in normalized:
            return Laterality.LEFT
        if "right" in normalized:
            return Laterality.RIGHT
        if "bilateral" in normalized or "both" in normalized:
            return Laterality.BILATERAL
    return Laterality.UNKNOWN


def normalize_ordering_specialty(value: str | None) -> OrderingSpecialty:
    normalized = _normalize_token(value)
    if normalized in SPECIALTY_ALIASES:
        return SPECIALTY_ALIASES[normalized]
    return OrderingSpecialty.OTHER


def normalize_structured_case(payload: StructuredCasePayload) -> NormalizedCasePayload:
    payer_id = normalize_payer_id(payload.payer, payload.payer_id)
    payer_name = normalize_payer_name(payload.payer, payer_id)
    fallback_text = payload.requested_study or payload.raw_clinical_note

    return NormalizedCasePayload(
        case_id=(payload.case_id or "unknown-case").strip(),
        payer_id=payer_id.value,
        payer_name=payer_name,
        requested_modality=normalize_modality(payload.requested_modality, fallback_text).value,
        requested_body_region=normalize_body_region(payload.requested_body_region, fallback_text).value,
        requested_laterality=normalize_laterality(payload.requested_laterality, payload.raw_clinical_note).value,
        ordering_specialty=normalize_ordering_specialty(payload.ordering_specialty).value,
        raw_clinical_note=(payload.raw_clinical_note or "").strip() or (payload.reason_for_order or "").strip(),
        diagnosis=payload.diagnosis,
        reason_for_order=payload.reason_for_order,
        symptom_duration_weeks=payload.symptom_duration_weeks,
        demographics=payload.demographics,
        prior_treatments=payload.prior_treatments,
        prior_imaging=payload.prior_imaging,
        structured_intake={
            "requested_study": payload.requested_study,
            **payload.additional_fields,
        },
    )


def normalize_text_case(payload: TextCasePayload) -> NormalizedCasePayload:
    metadata = payload.metadata
    payer_id = normalize_payer_id(metadata.get("payer"), metadata.get("payer_id"))
    payer_name = normalize_payer_name(metadata.get("payer"), payer_id)
    fallback_text = metadata.get("requested_study") or payload.raw_clinical_note

    return NormalizedCasePayload(
        case_id=metadata.get("case_id", "unknown-case").strip(),
        payer_id=payer_id.value,
        payer_name=payer_name,
        requested_modality=normalize_modality(metadata.get("requested_modality"), fallback_text).value,
        requested_body_region=normalize_body_region(metadata.get("requested_body_region"), fallback_text).value,
        requested_laterality=normalize_laterality(metadata.get("requested_laterality"), payload.raw_clinical_note).value,
        ordering_specialty=normalize_ordering_specialty(metadata.get("ordering_specialty")).value,
        raw_clinical_note=payload.raw_clinical_note,
        diagnosis=metadata.get("diagnosis"),
        reason_for_order=metadata.get("reason_for_order"),
        symptom_duration_weeks=int(metadata["symptom_duration_weeks"]) if metadata.get("symptom_duration_weeks") else None,
        demographics={},
        prior_treatments=[],
        prior_imaging=[],
        structured_intake=dict(metadata),
    )


def normalize_case_payload(payload: StructuredCasePayload | TextCasePayload) -> NormalizedCasePayload:
    if isinstance(payload, StructuredCasePayload):
        return normalize_structured_case(payload)
    return normalize_text_case(payload)
