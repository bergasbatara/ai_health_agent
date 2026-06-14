from __future__ import annotations

import re

from domain import PolicyDocument

from .models import PolicyChunk, RawPolicyDocument


SECTION_PATTERN = re.compile(r"^[A-Z][A-Z0-9\s/&()\-]{4,}$")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_into_word_windows(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = normalized.split(" ")
    if len(words) <= chunk_size:
        return [normalized]

    windows: list[str] = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        window_words = words[start : start + chunk_size]
        if not window_words:
            continue
        windows.append(" ".join(window_words))
        if start + chunk_size >= len(words):
            break
    return windows


def infer_section_label(page_text: str) -> str | None:
    for line in page_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if SECTION_PATTERN.match(candidate):
            return candidate.title()
        if ":" in candidate and len(candidate) <= 120:
            return candidate.split(":", 1)[0].strip().title()
        break
    return None


def build_chunk_id(document_id: str, page_number: int, chunk_index: int) -> str:
    return f"{document_id}-p{page_number}-c{chunk_index}"


def chunk_document(
    raw_document: RawPolicyDocument,
    document: PolicyDocument,
    *,
    chunk_size: int = 200,
    overlap: int = 40,
) -> list[PolicyChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[PolicyChunk] = []
    for page in raw_document.pages:
        windows = split_into_word_windows(page.text, chunk_size=chunk_size, overlap=overlap)
        if not windows:
            continue

        section_label = infer_section_label(page.text)
        for chunk_index, text in enumerate(windows):
            chunks.append(
                PolicyChunk(
                    chunk_id=build_chunk_id(document.document_id, page.page_number, chunk_index),
                    document_id=document.document_id,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    text=text,
                    section_label=section_label,
                    study_family=document.study_family,
                    retrieval_metadata={
                        "payer_id": document.payer_id,
                        "payer_name": document.payer_name,
                        "title": document.title,
                        "source_path": document.source_path,
                        "study_family": document.study_family,
                        "requested_modality": str(document.retrieval_metadata.get("requested_modality", "")),
                        "requested_body_region": str(document.retrieval_metadata.get("requested_body_region", "")),
                    },
                )
            )
    return chunks
