from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import DiscoveredPdf, RawPolicyDocument, RawPolicyPage


def build_document_id(pdf: DiscoveredPdf) -> str:
    filename = Path(pdf.filename).stem.casefold()
    normalized = "".join(char if char.isalnum() else "-" for char in filename)
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or pdf.checksum_sha256[:12]


def _load_pdf_reader():
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError(
            "pypdf is required for PDF loading. Install dependencies with `pip install -e .` "
            "or `pip install pypdf`."
        ) from exc
    return PdfReader


def _normalize_pdf_metadata(metadata: Any) -> dict[str, str]:
    if not metadata:
        return {}

    normalized: dict[str, str] = {}
    for key, value in dict(metadata).items():
        if value is None:
            continue
        cleaned_key = str(key).lstrip("/")
        normalized[cleaned_key] = str(value)
    return normalized


def load_pdf(pdf: DiscoveredPdf) -> RawPolicyDocument:
    PdfReader = _load_pdf_reader()
    reader = PdfReader(str(pdf.path))

    pages: list[RawPolicyPage] = []
    for index, page in enumerate(reader.pages, start=1):
        extracted_text = page.extract_text() or ""
        pages.append(RawPolicyPage(page_number=index, text=extracted_text.strip()))

    return RawPolicyDocument(
        document_id=build_document_id(pdf),
        source_pdf=pdf,
        page_count=len(pages),
        pages=pages,
        pdf_metadata=_normalize_pdf_metadata(getattr(reader, "metadata", None)),
    )
