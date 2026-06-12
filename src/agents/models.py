from __future__ import annotations

from pydantic import Field, field_validator

from domain import (
    ExtractedClinicalFacts,
    PatientCase,
    PolicyEvidence,
    PolicyMatchResult,
    PriorAuthDraft,
)
from domain.models import DomainModel


class ExtractorInput(DomainModel):
    patient_case: PatientCase


class ExtractorOutput(DomainModel):
    extracted_facts: ExtractedClinicalFacts
    reasoning_summary: str | None = None


class PolicyMatcherInput(DomainModel):
    patient_case: PatientCase
    extracted_facts: ExtractedClinicalFacts
    policy_evidence: list[PolicyEvidence] = Field(default_factory=list)


class PolicyMatcherOutput(DomainModel):
    policy_match_result: PolicyMatchResult
    reasoning_summary: str | None = None

    @field_validator("policy_match_result")
    @classmethod
    def policy_match_must_have_evidence(cls, value: PolicyMatchResult) -> PolicyMatchResult:
        if not value.cited_evidence:
            raise ValueError("policy_match_result must include cited_evidence")
        return value


class FormFillerInput(DomainModel):
    patient_case: PatientCase
    extracted_facts: ExtractedClinicalFacts
    policy_match_result: PolicyMatchResult


class FormFillerOutput(DomainModel):
    prior_auth_draft: PriorAuthDraft
    reasoning_summary: str | None = None

