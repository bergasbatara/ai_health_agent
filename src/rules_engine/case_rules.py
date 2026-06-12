from __future__ import annotations

from domain import ClinicalStatus, ExtractedClinicalFacts, PatientCase

from .common import evaluate_checks, make_error, make_rule_check, make_warning
from .models import RuleCheckResult, RulesEvaluationResult


def check_required_case_fields(patient_case: PatientCase) -> RuleCheckResult:
    issues = []
    if not patient_case.payer_name.strip():
        issues.append(make_error("missing_payer_name", "Payer name is required.", "patient_case.payer_name"))
    if not str(patient_case.requested_modality).strip():
        issues.append(make_error("missing_requested_modality", "Requested modality is required.", "patient_case.requested_modality"))
    if not str(patient_case.requested_body_region).strip():
        issues.append(make_error("missing_requested_body_region", "Requested body region is required.", "patient_case.requested_body_region"))
    if not patient_case.raw_clinical_note.strip():
        issues.append(make_error("missing_raw_clinical_note", "Raw clinical note is required.", "patient_case.raw_clinical_note"))
    return make_rule_check("check_required_case_fields", issues)


def check_conservative_therapy_duration(
    patient_case: PatientCase,
    extracted_facts: ExtractedClinicalFacts,
) -> RuleCheckResult:
    issues = []
    if extracted_facts.conservative_therapy_completed == ClinicalStatus.YES:
        relevant_treatments = [item for item in patient_case.prior_treatments if item.duration_weeks is not None]
        if not relevant_treatments:
            issues.append(
                make_warning(
                    "missing_conservative_therapy_duration",
                    "Conservative therapy is marked completed, but no treatment duration is documented.",
                    "patient_case.prior_treatments",
                )
            )
        elif max(item.duration_weeks or 0 for item in relevant_treatments) < 6:
            issues.append(
                make_warning(
                    "conservative_therapy_duration_below_threshold",
                    "Conservative therapy duration is documented below the expected 6-week prototype threshold.",
                    "patient_case.prior_treatments",
                )
            )
    return make_rule_check("check_conservative_therapy_duration", issues)


def check_prior_imaging_consistency(
    patient_case: PatientCase,
    extracted_facts: ExtractedClinicalFacts,
) -> RuleCheckResult:
    issues = []
    if extracted_facts.prior_imaging_completed == ClinicalStatus.YES and not patient_case.prior_imaging:
        issues.append(
            make_warning(
                "prior_imaging_claim_without_record",
                "Prior imaging is marked completed, but no prior imaging record is present in the case.",
                "patient_case.prior_imaging",
            )
        )
    return make_rule_check("check_prior_imaging_consistency", issues)


def evaluate_case_rules(
    patient_case: PatientCase,
    extracted_facts: ExtractedClinicalFacts,
) -> RulesEvaluationResult:
    checks = [
        check_required_case_fields(patient_case),
        check_conservative_therapy_duration(patient_case, extracted_facts),
        check_prior_imaging_consistency(patient_case, extracted_facts),
    ]
    return evaluate_checks(checks)
