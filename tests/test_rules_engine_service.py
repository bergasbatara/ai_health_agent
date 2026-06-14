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
    RecommendationSignal,
    ReviewStatus,
)
from rules_engine import RulesEngineServiceResult, evaluate_prior_auth_package


def make_policy_evidence() -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id="evidence-1",
        document_id="aetna-knee-mri-policy",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
        relevance_score=0.91,
        page_number=2,
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
        "prior_treatments": [
            {
                "treatment_type": "physical_therapy",
                "completed": "yes",
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


def make_extracted_facts(**overrides) -> ExtractedClinicalFacts:
    payload = {
        "case_id": "case-001",
        "requested_modality": ImagingModality.MRI,
        "requested_body_region": BodyRegion.KNEE,
        "requested_laterality": Laterality.LEFT,
        "symptom_duration_weeks": 8,
        "conservative_therapy_completed": ClinicalStatus.YES,
        "prior_imaging_completed": ClinicalStatus.YES,
        "red_flags_present": ClinicalStatus.NO,
        "contraindications_present": ClinicalStatus.UNKNOWN,
    }
    payload.update(overrides)
    return ExtractedClinicalFacts(**payload)


def make_policy_match_result(**overrides) -> PolicyMatchResult:
    evidence = make_policy_evidence()
    payload = {
        "case_id": "case-001",
        "payer_id": PayerId.AETNA,
        "payer_name": "Aetna",
        "requested_modality": ImagingModality.MRI,
        "requested_body_region": BodyRegion.KNEE,
        "requested_laterality": Laterality.LEFT,
        "recommendation_signal": RecommendationSignal.NEEDS_MORE_INFO,
        "policy_requirements_summary": "Knee MRI requires conservative treatment and prior imaging review.",
        "criteria": [
            CoverageCriterion(
                criterion_key="conservative_therapy_completed",
                display_name="Conservative therapy completed",
                status=CriterionStatus.MET,
                rationale="PT documented for 6 weeks.",
                policy_evidence=[evidence],
            )
        ],
        "unresolved_questions": [],
        "cited_evidence": [evidence],
    }
    payload.update(overrides)
    return PolicyMatchResult(**payload)


def make_prior_auth_draft(**overrides) -> PriorAuthDraft:
    payload = {
        "case_id": "case-001",
        "review_status": ReviewStatus.NEEDS_REVIEW,
        "reviewer_summary": "Draft generated for review.",
        "missing_requirements": [],
        "unresolved_issues": [],
        "risk_flags": [],
    }
    payload.update(overrides)
    return PriorAuthDraft(**payload)


def test_evaluate_prior_auth_package_returns_aggregate_result():
    result = evaluate_prior_auth_package(
        make_patient_case(),
        make_extracted_facts(),
        make_policy_match_result(),
        make_prior_auth_draft(),
    )

    assert isinstance(result, RulesEngineServiceResult)
    assert result.passed is True
    assert len(result.case_evaluation.checks) == 3
    assert len(result.policy_evaluation.checks) == 3
    assert len(result.draft_evaluation.checks) == 4
    assert len(result.checks) == 10
    assert result.issues == []


def test_evaluate_prior_auth_package_flattens_stage_issues():
    result = evaluate_prior_auth_package(
        make_patient_case(prior_treatments=[{"treatment_type": "physical_therapy", "completed": "yes"}], prior_imaging=[]),
        make_extracted_facts(prior_imaging_completed=ClinicalStatus.YES),
        make_policy_match_result(
            recommendation_signal=RecommendationSignal.LIKELY_APPROVE,
            criteria=[
                {
                    "criterion_key": "conservative_therapy_completed",
                    "display_name": "Conservative therapy completed",
                    "status": "not_met",
                    "rationale": "PT not documented.",
                    "policy_evidence": [make_policy_evidence()],
                }
            ],
        ),
        make_prior_auth_draft(review_status=ReviewStatus.READY_FOR_SUBMISSION),
    )

    issue_codes = {issue.code for issue in result.issues}

    assert result.passed is False
    assert "missing_conservative_therapy_duration" in issue_codes
    assert "prior_imaging_claim_without_record" in issue_codes
    assert "inconsistent_recommendation_signal" in issue_codes
    assert "missing_draft_requirements" in issue_codes
    assert "draft_marked_ready_with_blockers" in issue_codes
