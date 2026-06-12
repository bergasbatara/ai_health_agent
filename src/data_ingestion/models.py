from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_serializer

from domain import PayerId
from domain.models import PolicyDocument
from domain.models import DomainModel


class DiscoveredPdf(DomainModel):
    path: Path
    filename: str = Field(min_length=1)
    payer_id: PayerId
    checksum_sha256: str = Field(min_length=64, max_length=64)

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        return str(path)


class RawPolicyPage(DomainModel):
    page_number: int = Field(ge=1)
    text: str = ""


class RawPolicyDocument(DomainModel):
    document_id: str = Field(min_length=1)
    source_pdf: DiscoveredPdf
    page_count: int = Field(ge=0)
    pages: list[RawPolicyPage] = Field(default_factory=list)
    pdf_metadata: dict[str, str] = Field(default_factory=dict)


class PolicyChunk(DomainModel):
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    section_label: str | None = None
    study_family: str = Field(min_length=1)
    retrieval_metadata: dict[str, str | int] = Field(default_factory=dict)


class EmbeddedChunk(DomainModel):
    chunk: PolicyChunk
    embedding: list[float] = Field(default_factory=list)


class IngestionReport(DomainModel):
    document: PolicyDocument
    chunk_count: int = Field(ge=0)
    indexed_chunk_ids: list[str] = Field(default_factory=list)
