from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_serializer

from domain import PayerId
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
