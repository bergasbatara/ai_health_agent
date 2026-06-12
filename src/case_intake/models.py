from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_serializer, model_validator

from domain.models import DomainModel


class RawCaseFile(DomainModel):
    path: Path
    filename: str = Field(min_length=1)
    file_format: Literal["json", "text"]
    content: str = Field(min_length=1)

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        return str(path)


class StructuredCasePayload(DomainModel):
    case_id: str | None = None
    payer: str | None = None
    payer_id: str | None = None
    requested_study: str | None = None
    requested_modality: str | None = None
    requested_body_region: str | None = None
    requested_laterality: str | None = None
    ordering_specialty: str | None = None
    raw_clinical_note: str | None = None
    diagnosis: str | None = None
    reason_for_order: str | None = None
    symptom_duration_weeks: int | None = Field(default=None, ge=0)
    demographics: dict[str, Any] = Field(default_factory=dict)
    prior_treatments: list[dict[str, Any]] = Field(default_factory=list)
    prior_imaging: list[dict[str, Any]] = Field(default_factory=list)
    additional_fields: dict[str, Any] = Field(default_factory=dict)


class TextCasePayload(DomainModel):
    metadata: dict[str, str] = Field(default_factory=dict)
    raw_clinical_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def metadata_values_must_be_non_blank(self) -> "TextCasePayload":
        cleaned: dict[str, str] = {}
        for key, value in self.metadata.items():
            normalized_key = key.strip()
            normalized_value = value.strip()
            if not normalized_key:
                raise ValueError("metadata keys must not be blank")
            if not normalized_value:
                raise ValueError("metadata values must not be blank")
            cleaned[normalized_key] = normalized_value
        self.metadata = cleaned
        return self


class NormalizedCasePayload(DomainModel):
    case_id: str = Field(min_length=1)
    payer_id: str = Field(min_length=1)
    payer_name: str = Field(min_length=1)
    requested_modality: str = Field(min_length=1)
    requested_body_region: str = Field(min_length=1)
    requested_laterality: str = Field(min_length=1)
    ordering_specialty: str = Field(min_length=1)
    raw_clinical_note: str = Field(min_length=1)
    diagnosis: str | None = None
    reason_for_order: str | None = None
    symptom_duration_weeks: int | None = Field(default=None, ge=0)
    demographics: dict[str, Any] = Field(default_factory=dict)
    prior_treatments: list[dict[str, Any]] = Field(default_factory=list)
    prior_imaging: list[dict[str, Any]] = Field(default_factory=list)
    structured_intake: dict[str, Any] = Field(default_factory=dict)
