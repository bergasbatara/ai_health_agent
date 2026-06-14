from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from domain.models import DomainModel


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(DomainModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: IssueSeverity
    field_path: str | None = None


class RuleCheckResult(DomainModel):
    rule_name: str = Field(min_length=1)
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class RulesEvaluationResult(DomainModel):
    passed: bool
    checks: list[RuleCheckResult] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)


class RulesEngineServiceResult(DomainModel):
    passed: bool
    case_evaluation: RulesEvaluationResult
    policy_evaluation: RulesEvaluationResult
    draft_evaluation: RulesEvaluationResult
    checks: list[RuleCheckResult] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
