from __future__ import annotations

import re
from datetime import date

from domain import BodyRegion, ImagingModality, PolicyDocument, PayerId

from .models import RawPolicyDocument


VERSION_PATTERN = re.compile(r"\b(v(?:ersion)?\.?\s*\d+(?:\.\d+){0,3})\b", re.IGNORECASE)
YYYY_MM_DD_PATTERN = re.compile(r"\b(20\d{2})[._-](\d{2})[._-](\d{2})\b")
MM_DD_YYYY_PATTERN = re.compile(r"\b(\d{2})[._-](\d{2})[._-](20\d{2})\b")
MONTH_YYYY_PATTERN = re.compile(
    r"\b("
    r"january|february|march|april|may|june|july|august|september|october|november|december"
    r")[\s_-]+(20\d{2})\b",
    re.IGNORECASE,
)


def get_searchable_text(raw_document: RawPolicyDocument) -> str:
    page_text = "\n".join(page.text for page in raw_document.pages if page.text)
    metadata_text = "\n".join(raw_document.pdf_metadata.values())
    return "\n".join(filter(None, [raw_document.source_pdf.filename, metadata_text, page_text]))


def infer_payer_name(raw_document: RawPolicyDocument) -> str:
    if raw_document.source_pdf.payer_id == PayerId.AETNA:
        return "Aetna"
    if raw_document.source_pdf.payer_id == PayerId.CIGNA:
        return "Cigna"
    if raw_document.source_pdf.payer_id == PayerId.MEDADV:
        return "MedAdv"
    title = raw_document.pdf_metadata.get("Title")
    if title:
        return title.split()[0]
    return "Unknown Payer"


def infer_title(raw_document: RawPolicyDocument) -> str:
    metadata_title = raw_document.pdf_metadata.get("Title")
    if metadata_title:
        return metadata_title.strip()
    return raw_document.source_pdf.filename.rsplit(".", 1)[0].replace("_", " ").strip()


def infer_version(raw_document: RawPolicyDocument) -> str | None:
    searchable_text = get_searchable_text(raw_document)
    match = VERSION_PATTERN.search(searchable_text)
    if match:
        return re.sub(r"\s+", "", match.group(1)).upper().replace("VERSION", "V")
    return None


def _build_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def infer_effective_date(raw_document: RawPolicyDocument) -> date | None:
    searchable_text = get_searchable_text(raw_document)

    for match in MM_DD_YYYY_PATTERN.finditer(searchable_text):
        month, day, year = map(int, match.groups())
        parsed = _build_date(year, month, day)
        if parsed:
            return parsed

    for match in YYYY_MM_DD_PATTERN.finditer(searchable_text):
        year, month, day = map(int, match.groups())
        parsed = _build_date(year, month, day)
        if parsed:
            return parsed

    month_lookup = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    match = MONTH_YYYY_PATTERN.search(searchable_text)
    if match:
        month = month_lookup[match.group(1).casefold()]
        year = int(match.group(2))
        return date(year, month, 1)

    return None


def infer_study_family(raw_document: RawPolicyDocument) -> str:
    searchable_text = get_searchable_text(raw_document).casefold()
    if "knee" in searchable_text and "mri" in searchable_text:
        return "knee_mri"
    if "musculoskeletal" in searchable_text and "imaging" in searchable_text:
        return "musculoskeletal_imaging"
    if "rad" in searchable_text or "radiology" in searchable_text:
        return "general_radiology"
    return "general_imaging"


def infer_requested_modality(raw_document: RawPolicyDocument) -> str:
    searchable_text = get_searchable_text(raw_document).casefold()
    if "mri" in searchable_text or "magnetic resonance" in searchable_text:
        return ImagingModality.MRI
    if "ct" in searchable_text or "computed tomography" in searchable_text:
        return ImagingModality.CT
    if "x-ray" in searchable_text or "xray" in searchable_text or "radiograph" in searchable_text:
        return ImagingModality.XRAY
    if "ultrasound" in searchable_text:
        return ImagingModality.ULTRASOUND
    return ImagingModality.OTHER


def infer_requested_body_region(raw_document: RawPolicyDocument) -> str:
    searchable_text = get_searchable_text(raw_document).casefold()
    if "knee" in searchable_text:
        return BodyRegion.KNEE
    if "shoulder" in searchable_text:
        return BodyRegion.SHOULDER
    if "lumbar" in searchable_text or "low back" in searchable_text:
        return BodyRegion.LUMBAR_SPINE
    if "cervical" in searchable_text or "neck" in searchable_text:
        return BodyRegion.CERVICAL_SPINE
    if "thoracic" in searchable_text or "mid back" in searchable_text:
        return BodyRegion.THORACIC_SPINE
    if "hip" in searchable_text:
        return BodyRegion.HIP
    if "head" in searchable_text or "brain" in searchable_text:
        return BodyRegion.HEAD
    return BodyRegion.OTHER


def build_policy_document(raw_document: RawPolicyDocument) -> PolicyDocument:
    requested_modality = infer_requested_modality(raw_document)
    requested_body_region = infer_requested_body_region(raw_document)
    return PolicyDocument(
        document_id=raw_document.document_id,
        payer_id=raw_document.source_pdf.payer_id,
        payer_name=infer_payer_name(raw_document),
        title=infer_title(raw_document),
        source_path=str(raw_document.source_pdf.path),
        study_family=infer_study_family(raw_document),
        version=infer_version(raw_document),
        effective_date=infer_effective_date(raw_document),
        retrieval_metadata={
            "filename": raw_document.source_pdf.filename,
            "page_count": raw_document.page_count,
            "checksum_sha256": raw_document.source_pdf.checksum_sha256,
            "pdf_metadata": raw_document.pdf_metadata,
            "requested_modality": requested_modality,
            "requested_body_region": requested_body_region,
        },
    )
