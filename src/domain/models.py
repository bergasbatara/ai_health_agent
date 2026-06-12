from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    BodyRegion,
    ClinicalStatus,
    CriterionStatus,
    ImagingModality,
    Laterality,
    OrderingSpecialty,
    PayerId,
    RecommendationSignal,
    ReviewStatus,
)


class DomainModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)


class PriorTreatment(DomainModel):
    treatment_type: str = Field(min_length=1)
    completed: ClinicalStatus = ClinicalStatus.UNKNOWN
    duration_weeks: int | None = Field(default=None, ge=0)
    notes: str | None = None


class PriorImagingStudy(DomainModel):
    modality: ImagingModality
    body_region: BodyRegion
    laterality: Laterality = Laterality.UNKNOWN
    result_summary: str | None = None
    performed_date: date | None = None


class Demographics(DomainModel):
    age_years: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = None


class PatientCase(DomainModel):
    case_id: str = Field(min_length=1)
    payer_id: PayerId
    payer_name: str = Field(min_length=1)
    requested_modality: ImagingModality
    requested_body_region: BodyRegion
    requested_laterality: Laterality = Laterality.UNKNOWN
    ordering_specialty: OrderingSpecialty
    raw_clinical_note: str = Field(min_length=1)
    demographics: Demographics = Field(default_factory=Demographics)
    diagnosis: str | None = None
    reason_for_order: str | None = None
    symptom_duration_weeks: int | None = Field(default=None, ge=0)
    prior_treatments: list[PriorTreatment] = Field(default_factory=list)
    prior_imaging: list[PriorImagingStudy] = Field(default_factory=list)
    structured_intake: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payer_name(self) -> "PatientCase":
        if not self.payer_name.strip():
            raise ValueError("payer_name must not be blank")
        return self


class PolicyDocument(DomainModel):
    document_id: str = Field(min_length=1)
    payer_id: PayerId
    payer_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    version: str | None = None
    effective_date: date | None = None
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyEvidence(DomainModel):
    evidence_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    citation_text: str = Field(min_length=1)
    section_label: str | None = None
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    page_number: int | None = Field(default=None, ge=1)


class ClinicalFact(DomainModel):
    fact_key: str = Field(min_length=1)
    value: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_note_excerpt: str | None = None


class ExtractedClinicalFacts(DomainModel):
    case_id: str = Field(min_length=1)
    requested_modality: ImagingModality
    requested_body_region: BodyRegion
    requested_laterality: Laterality = Laterality.UNKNOWN
    symptom_duration_weeks: int | None = Field(default=None, ge=0)
    symptom_duration_status: ClinicalStatus = ClinicalStatus.UNKNOWN
    conservative_therapy_completed: ClinicalStatus = ClinicalStatus.UNKNOWN
    prior_imaging_completed: ClinicalStatus = ClinicalStatus.UNKNOWN
    red_flags_present: ClinicalStatus = ClinicalStatus.UNKNOWN
    contraindications_present: ClinicalStatus = ClinicalStatus.UNKNOWN
    diagnosis: str | None = None
    reason_for_order: str | None = None
    supporting_facts: list[ClinicalFact] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)

    @field_validator("missing_facts")
    @classmethod
    def missing_fact_keys_must_be_non_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("missing_facts must not contain blank entries")
        return value

    @model_validator(mode="after")
    def infer_symptom_duration_status(self) -> "ExtractedClinicalFacts":
        if self.symptom_duration_weeks is None:
            self.symptom_duration_status = ClinicalStatus.UNKNOWN
        else:
            self.symptom_duration_status = ClinicalStatus.YES
        return self


class CoverageCriterion(DomainModel):
    criterion_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    status: CriterionStatus
    rationale: str = Field(min_length=1)
    policy_evidence: list[PolicyEvidence] = Field(default_factory=list)
    patient_supporting_facts: list[ClinicalFact] = Field(default_factory=list)


class PolicyMatchResult(DomainModel):
    case_id: str = Field(min_length=1)
    payer_id: PayerId
    payer_name: str = Field(min_length=1)
    requested_modality: ImagingModality
    requested_body_region: BodyRegion
    requested_laterality: Laterality = Laterality.UNKNOWN
    recommendation_signal: RecommendationSignal = RecommendationSignal.UNCLEAR
    policy_requirements_summary: str = Field(min_length=1)
    criteria: list[CoverageCriterion] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    cited_evidence: list[PolicyEvidence] = Field(default_factory=list)

    @field_validator("unresolved_questions")
    @classmethod
    def unresolved_questions_must_be_non_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("unresolved_questions must not contain blank entries")
        return value


class DraftFormField(DomainModel):
    field_name: str = Field(min_length=1)
    field_value: str = Field(min_length=1)
    source: str | None = None


class PriorAuthDraft(DomainModel):
    case_id: str = Field(min_length=1)
    review_status: ReviewStatus = ReviewStatus.DRAFT
    reviewer_summary: str = Field(min_length=1)
    form_fields: list[DraftFormField] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    submission_notes: str | None = None

    @field_validator("missing_requirements", "unresolved_issues", "risk_flags")
    @classmethod
    def list_entries_must_be_non_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("list values must not contain blank entries")
        return value
