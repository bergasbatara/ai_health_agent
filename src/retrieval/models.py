from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from domain import PolicyEvidence
from domain.models import DomainModel


class PolicySearchQuery(DomainModel):
    query_text: str = Field(min_length=1)
    payer_id: str | None = None
    requested_modality: str | None = None
    requested_body_region: str | None = None
    study_family: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(DomainModel):
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    section_label: str | None = None
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(DomainModel):
    query: PolicySearchQuery
    hits: list[RetrievedChunk] = Field(default_factory=list)
    evidence: list[PolicyEvidence] = Field(default_factory=list)

    @field_validator("evidence")
    @classmethod
    def evidence_ids_must_be_unique(cls, value: list[PolicyEvidence]) -> list[PolicyEvidence]:
        seen_ids: set[str] = set()
        for item in value:
            if item.evidence_id in seen_ids:
                raise ValueError(f"Duplicate evidence_id in retrieval result: {item.evidence_id}")
            seen_ids.add(item.evidence_id)
        return value
