from __future__ import annotations

from domain import PatientCase

from .models import PolicySearchQuery


def infer_study_family(patient_case: PatientCase) -> str:
    if patient_case.requested_body_region == "knee" and patient_case.requested_modality == "mri":
        return "knee_mri"
    if patient_case.requested_modality == "mri":
        return f"{patient_case.requested_body_region}_mri"
    return f"{patient_case.requested_body_region}_{patient_case.requested_modality}"


def build_query_text(patient_case: PatientCase) -> str:
    parts = [
        patient_case.payer_name,
        patient_case.requested_body_region,
        patient_case.requested_modality,
        "prior authorization policy",
    ]

    if patient_case.reason_for_order:
        parts.append(patient_case.reason_for_order)
    if patient_case.diagnosis:
        parts.append(patient_case.diagnosis)
    if patient_case.symptom_duration_weeks is not None:
        parts.append(f"symptoms {patient_case.symptom_duration_weeks} weeks")
    if patient_case.prior_treatments:
        parts.append("conservative therapy")
    if patient_case.prior_imaging:
        parts.append("prior imaging")

    return " ".join(str(part).strip() for part in parts if str(part).strip())


def build_query_filters(patient_case: PatientCase, study_family: str) -> dict[str, str]:
    return {
        "payer_id": str(patient_case.payer_id),
        "requested_modality": str(patient_case.requested_modality),
        "requested_body_region": str(patient_case.requested_body_region),
        "study_family": study_family,
    }


def build_policy_search_query(patient_case: PatientCase, top_k: int = 5) -> PolicySearchQuery:
    study_family = infer_study_family(patient_case)
    return PolicySearchQuery(
        query_text=build_query_text(patient_case),
        payer_id=str(patient_case.payer_id),
        requested_modality=str(patient_case.requested_modality),
        requested_body_region=str(patient_case.requested_body_region),
        study_family=study_family,
        top_k=top_k,
        filters=build_query_filters(patient_case, study_family),
    )
