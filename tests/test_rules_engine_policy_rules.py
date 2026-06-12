from rules_engine import (
    check_criteria_have_rationale_and_evidence,
    check_policy_result_has_citations,
    check_recommendation_signal_consistency,
    evaluate_policy_rules,
)
from domain import (
    BodyRegion,
    CoverageCriterion,
    CriterionStatus,
    ImagingModality,
    PolicyEvidence,
    PolicyMatchResult,
    RecommendationSignal,
    PayerId,
)


def make_policy_evidence() -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id="evidence-1",
        document_id="aetna-knee-mri-policy",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
        relevance_score=0.91,
        page_number=2,
    )


def make_policy_match_result(**overrides) -> PolicyMatchResult:
    evidence = make_policy_evidence()
    payload = {
        "case_id": "case-001",
        "payer_id": PayerId.AETNA,
        "payer_name": "Aetna",
        "requested_modality": ImagingModality.MRI,
        "requested_body_region": BodyRegion.KNEE,
        "policy_requirements_summary": "Knee MRI requires conservative treatment.",
        "criteria": [
            CoverageCriterion(
                criterion_key="conservative_therapy_completed",
                display_name="Conservative therapy completed",
                status=CriterionStatus.MET,
                rationale="PT documented for 6 weeks.",
                policy_evidence=[evidence],
            )
        ],
        "cited_evidence": [evidence],
    }
    payload.update(overrides)
    return PolicyMatchResult(**payload)


def test_policy_result_has_citations_passes_when_evidence_present():
    check = check_policy_result_has_citations(make_policy_match_result())

    assert check.passed is True
    assert check.issues == []


def test_criteria_rationale_and_evidence_check_flags_missing_support():
    check = check_criteria_have_rationale_and_evidence(
        make_policy_match_result(
            criteria=[
                {
                    "criterion_key": "conservative_therapy_completed",
                    "display_name": "Conservative therapy completed",
                    "status": "met",
                    "rationale": "PT documented for 6 weeks.",
                    "policy_evidence": [],
                }
            ]
        )
    )

    assert check.passed is False
    assert check.issues[0].code == "missing_criterion_evidence"


def test_recommendation_signal_consistency_flags_approval_with_not_met_criterion():
    check = check_recommendation_signal_consistency(
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
        )
    )

    assert check.passed is False
    assert check.issues[0].code == "inconsistent_recommendation_signal"


def test_evaluate_policy_rules_aggregates_checks():
    result = evaluate_policy_rules(
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
        )
    )

    assert len(result.checks) == 3
    assert result.passed is False
