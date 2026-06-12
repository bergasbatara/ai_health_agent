from rules_engine import (
    check_draft_has_review_status,
    check_draft_missing_requirements_consistency,
    check_draft_review_state_consistency,
    check_draft_unresolved_issues_consistency,
    evaluate_draft_rules,
)
from domain import (
    BodyRegion,
    CoverageCriterion,
    CriterionStatus,
    ImagingModality,
    PolicyEvidence,
    PolicyMatchResult,
    PriorAuthDraft,
    ReviewStatus,
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
        "unresolved_questions": [],
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


def test_draft_has_review_status_passes_for_valid_draft():
    check = check_draft_has_review_status(make_prior_auth_draft())

    assert check.passed is True
    assert check.issues == []


def test_draft_unresolved_issues_consistency_warns_when_unknowns_exist():
    draft = make_prior_auth_draft(unresolved_issues=[])
    policy_match_result = make_policy_match_result(
        criteria=[
            {
                "criterion_key": "conservative_therapy_completed",
                "display_name": "Conservative therapy completed",
                "status": "unknown",
                "rationale": "Unable to confirm therapy duration.",
                "policy_evidence": [make_policy_evidence()],
            }
        ]
    )

    check = check_draft_unresolved_issues_consistency(draft, policy_match_result)

    assert check.passed is True
    assert check.issues[0].code == "missing_unresolved_issues"


def test_draft_missing_requirements_consistency_warns_when_criteria_not_met():
    draft = make_prior_auth_draft(missing_requirements=[])
    policy_match_result = make_policy_match_result(
        criteria=[
            {
                "criterion_key": "conservative_therapy_completed",
                "display_name": "Conservative therapy completed",
                "status": "not_met",
                "rationale": "PT not documented.",
                "policy_evidence": [make_policy_evidence()],
            }
        ]
    )

    check = check_draft_missing_requirements_consistency(draft, policy_match_result)

    assert check.passed is True
    assert check.issues[0].code == "missing_draft_requirements"


def test_draft_review_state_consistency_errors_when_ready_with_blockers():
    draft = make_prior_auth_draft(review_status=ReviewStatus.READY_FOR_SUBMISSION)
    policy_match_result = make_policy_match_result(
        criteria=[
            {
                "criterion_key": "conservative_therapy_completed",
                "display_name": "Conservative therapy completed",
                "status": "not_met",
                "rationale": "PT not documented.",
                "policy_evidence": [make_policy_evidence()],
            }
        ]
    )

    check = check_draft_review_state_consistency(draft, policy_match_result)

    assert check.passed is False
    assert check.issues[0].code == "draft_marked_ready_with_blockers"


def test_evaluate_draft_rules_aggregates_checks():
    draft = make_prior_auth_draft(review_status=ReviewStatus.READY_FOR_SUBMISSION)
    policy_match_result = make_policy_match_result(
        criteria=[
            {
                "criterion_key": "conservative_therapy_completed",
                "display_name": "Conservative therapy completed",
                "status": "not_met",
                "rationale": "PT not documented.",
                "policy_evidence": [make_policy_evidence()],
            }
        ]
    )

    result = evaluate_draft_rules(draft, policy_match_result)

    assert len(result.checks) == 4
    assert result.passed is False
