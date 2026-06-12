from rules_engine import IssueSeverity, RuleCheckResult, RulesEvaluationResult, ValidationIssue


def test_validation_issue_captures_code_message_and_severity():
    issue = ValidationIssue(
        code="missing_required_field",
        message="Requested modality is required.",
        severity=IssueSeverity.ERROR,
        field_path="patient_case.requested_modality",
    )

    assert issue.code == "missing_required_field"
    assert issue.severity == IssueSeverity.ERROR
    assert issue.field_path == "patient_case.requested_modality"


def test_rule_check_result_groups_issues_under_one_rule():
    issue = ValidationIssue(
        code="missing_citation",
        message="Policy recommendation must include a citation.",
        severity=IssueSeverity.ERROR,
    )
    check = RuleCheckResult(
        rule_name="check_policy_result_has_citations",
        passed=False,
        issues=[issue],
    )

    assert check.rule_name == "check_policy_result_has_citations"
    assert check.passed is False
    assert check.issues[0].code == "missing_citation"


def test_rules_evaluation_result_can_hold_aggregate_checks_and_issues():
    issue = ValidationIssue(
        code="draft_not_ready",
        message="Draft contains unresolved issues.",
        severity=IssueSeverity.WARNING,
    )
    result = RulesEvaluationResult(
        passed=False,
        checks=[
            RuleCheckResult(
                rule_name="check_draft_review_state_consistency",
                passed=False,
                issues=[issue],
            )
        ],
        issues=[issue],
    )

    assert result.passed is False
    assert len(result.checks) == 1
    assert result.issues[0].severity == IssueSeverity.WARNING
