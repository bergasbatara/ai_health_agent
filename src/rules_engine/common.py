from __future__ import annotations

from .models import IssueSeverity, RuleCheckResult, RulesEvaluationResult, ValidationIssue


def make_issue(
    *,
    code: str,
    message: str,
    severity: IssueSeverity,
    field_path: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        severity=severity,
        field_path=field_path,
    )


def make_error(code: str, message: str, field_path: str | None = None) -> ValidationIssue:
    return make_issue(code=code, message=message, severity=IssueSeverity.ERROR, field_path=field_path)


def make_warning(code: str, message: str, field_path: str | None = None) -> ValidationIssue:
    return make_issue(code=code, message=message, severity=IssueSeverity.WARNING, field_path=field_path)


def make_rule_check(rule_name: str, issues: list[ValidationIssue] | None = None) -> RuleCheckResult:
    normalized_issues = issues or []
    passed = not any(issue.severity == IssueSeverity.ERROR for issue in normalized_issues)
    return RuleCheckResult(
        rule_name=rule_name,
        passed=passed,
        issues=normalized_issues,
    )


def collect_issues(checks: list[RuleCheckResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for check in checks:
        issues.extend(check.issues)
    return issues


def evaluate_checks(checks: list[RuleCheckResult]) -> RulesEvaluationResult:
    issues = collect_issues(checks)
    passed = all(check.passed for check in checks)
    return RulesEvaluationResult(
        passed=passed,
        checks=checks,
        issues=issues,
    )
