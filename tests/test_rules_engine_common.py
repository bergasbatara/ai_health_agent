from rules_engine import (
    IssueSeverity,
    RuleCheckResult,
    ValidationIssue,
    collect_issues,
    evaluate_checks,
    make_error,
    make_issue,
    make_rule_check,
    make_warning,
)


def test_issue_helpers_create_expected_severities():
    error = make_error("missing_required_field", "Requested modality is required.", "patient_case.requested_modality")
    warning = make_warning("draft_not_ready", "Draft contains unresolved issues.")
    custom = make_issue(code="custom_code", message="Custom issue.", severity=IssueSeverity.WARNING)

    assert error.severity == IssueSeverity.ERROR
    assert warning.severity == IssueSeverity.WARNING
    assert custom.code == "custom_code"


def test_make_rule_check_marks_error_issues_as_failed():
    check = make_rule_check(
        "check_required_case_fields",
        issues=[make_error("missing_required_field", "Requested modality is required.")],
    )

    assert check.rule_name == "check_required_case_fields"
    assert check.passed is False


def test_make_rule_check_allows_warning_only_checks_to_pass():
    check = make_rule_check(
        "check_draft_review_state_consistency",
        issues=[make_warning("draft_not_ready", "Draft contains unresolved issues.")],
    )

    assert check.passed is True
    assert check.issues[0].severity == IssueSeverity.WARNING


def test_collect_issues_and_evaluate_checks_aggregate_results():
    checks = [
        make_rule_check("check_one", issues=[make_warning("warn", "Warning issue.")]),
        make_rule_check("check_two", issues=[make_error("err", "Error issue.")]),
    ]

    issues = collect_issues(checks)
    result = evaluate_checks(checks)

    assert len(issues) == 2
    assert result.passed is False
    assert len(result.issues) == 2
