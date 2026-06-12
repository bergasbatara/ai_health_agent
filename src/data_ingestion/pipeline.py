from __future__ import annotations

from typing import Callable

from .chunker import chunk_document
from .discovery import discover_pdfs
from .embedder import embed_chunks
from .metadata import build_policy_document
from .models import (
    BatchIngestionReport,
    DiscoveredPdf,
    EmbeddedChunk,
    IngestionReport,
    RawPolicyDocument,
)
from .pdf_loader import load_pdf
from .vector_store import index_embedded_chunks


PdfLoader = Callable[[DiscoveredPdf], RawPolicyDocument]
EmbedChunks = Callable[..., list[EmbeddedChunk]]


def ingest_document(
    pdf: DiscoveredPdf,
    *,
    pdf_loader: PdfLoader = load_pdf,
    embed_chunks_fn: EmbedChunks = embed_chunks,
    vector_store=None,
    chunk_size: int = 200,
    overlap: int = 40,
    embedder=None,
) -> IngestionReport:
    raw_document = pdf_loader(pdf)
    policy_document = build_policy_document(raw_document)
    chunks = chunk_document(raw_document, policy_document, chunk_size=chunk_size, overlap=overlap)
    embedded_chunks = embed_chunks_fn(chunks, embedder=embedder)
    return index_embedded_chunks(embedded_chunks, policy_document, vector_store=vector_store)


def ingest_directory(
    data_dir: str,
    *,
    pdf_loader: PdfLoader = load_pdf,
    embed_chunks_fn: EmbedChunks = embed_chunks,
    vector_store=None,
    chunk_size: int = 200,
    overlap: int = 40,
    embedder=None,
) -> BatchIngestionReport:
    reports: list[IngestionReport] = []
    for pdf in discover_pdfs(data_dir):
        report = ingest_document(
            pdf,
            pdf_loader=pdf_loader,
            embed_chunks_fn=embed_chunks_fn,
            vector_store=vector_store,
            chunk_size=chunk_size,
            overlap=overlap,
            embedder=embedder,
        )
        reports.append(report)
    return BatchIngestionReport(reports=reports)
