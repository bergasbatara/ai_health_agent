from __future__ import annotations

from typing import Any

from domain import (
    ClinicalStatus,
    Demographics,
    ImagingModality,
    Laterality,
    PatientCase,
    PriorImagingStudy,
    PriorTreatment,
)
from domain.enums import BodyRegion, OrderingSpecialty, PayerId

from .models import NormalizedCasePayload


def _coerce_clinical_status(value: Any) -> ClinicalStatus:
    normalized = str(value or "").strip().casefold()
    if normalized in {"yes", "true", "completed", "done"}:
        return ClinicalStatus.YES
    if normalized in {"no", "false", "not_completed", "not done"}:
        return ClinicalStatus.NO
    return ClinicalStatus.UNKNOWN


def build_demographics(payload: dict[str, Any]) -> Demographics:
    return Demographics(
        age_years=payload.get("age_years"),
        sex=payload.get("sex"),
    )


def build_prior_treatments(items: list[dict[str, Any]]) -> list[PriorTreatment]:
    treatments: list[PriorTreatment] = []
    for item in items:
        if not item.get("treatment_type"):
            continue
        treatments.append(
            PriorTreatment(
                treatment_type=str(item["treatment_type"]).strip(),
                completed=_coerce_clinical_status(item.get("completed")),
                duration_weeks=item.get("duration_weeks"),
                notes=item.get("notes"),
            )
        )
    return treatments


def build_prior_imaging(items: list[dict[str, Any]]) -> list[PriorImagingStudy]:
    studies: list[PriorImagingStudy] = []
    for item in items:
        modality = item.get("modality")
        body_region = item.get("body_region")
        if not modality or not body_region:
            continue
        studies.append(
            PriorImagingStudy(
                modality=ImagingModality(str(modality).strip().casefold()),
                body_region=BodyRegion(str(body_region).strip().casefold()),
                laterality=Laterality(str(item.get("laterality", Laterality.UNKNOWN)).strip().casefold()),
                result_summary=item.get("result_summary"),
            )
        )
    return studies


def build_patient_case(payload: NormalizedCasePayload) -> PatientCase:
    return PatientCase(
        case_id=payload.case_id,
        payer_id=PayerId(payload.payer_id),
        payer_name=payload.payer_name,
        requested_modality=ImagingModality(payload.requested_modality),
        requested_body_region=BodyRegion(payload.requested_body_region),
        requested_laterality=Laterality(payload.requested_laterality),
        ordering_specialty=OrderingSpecialty(payload.ordering_specialty),
        raw_clinical_note=payload.raw_clinical_note,
        demographics=build_demographics(payload.demographics),
        diagnosis=payload.diagnosis,
        reason_for_order=payload.reason_for_order,
        symptom_duration_weeks=payload.symptom_duration_weeks,
        prior_treatments=build_prior_treatments(payload.prior_treatments),
        prior_imaging=build_prior_imaging(payload.prior_imaging),
        structured_intake=payload.structured_intake,
    )
