from __future__ import annotations

from domain import PolicyEvidence

from .models import RetrievedChunk


def build_evidence_id(hit: RetrievedChunk) -> str:
    return f"{hit.document_id}:{hit.chunk_id}"


def map_retrieved_chunk_to_policy_evidence(hit: RetrievedChunk) -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id=build_evidence_id(hit),
        document_id=hit.document_id,
        chunk_id=hit.chunk_id,
        citation_text=hit.text,
        section_label=hit.section_label,
        relevance_score=hit.relevance_score,
        page_number=hit.page_number,
    )


def map_retrieved_chunks_to_policy_evidence(hits: list[RetrievedChunk]) -> list[PolicyEvidence]:
    return [map_retrieved_chunk_to_policy_evidence(hit) for hit in hits]
