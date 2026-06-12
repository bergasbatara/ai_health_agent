from __future__ import annotations

from typing import Callable

from domain import PatientCase, PolicyEvidence

from .mappers import map_retrieved_chunks_to_policy_evidence
from .models import PolicySearchQuery, RetrievalResult, RetrievedChunk
from .query_builder import build_policy_search_query


SearchFunction = Callable[..., list[RetrievedChunk]]
QueryBuilder = Callable[[PatientCase, int], PolicySearchQuery]
EvidenceMapper = Callable[[list[RetrievedChunk]], list[PolicyEvidence]]
EmbedTextsFunction = Callable[[list[str]], list[list[float]]]


def retrieve_policy_evidence(
    patient_case: PatientCase,
    *,
    searcher,
    top_k: int = 5,
    query_builder: QueryBuilder = build_policy_search_query,
    evidence_mapper: EvidenceMapper = map_retrieved_chunks_to_policy_evidence,
    embed_texts_fn: EmbedTextsFunction | None = None,
) -> RetrievalResult:
    query = query_builder(patient_case, top_k)
    query_embedding = None
    if embed_texts_fn is not None:
        vectors = embed_texts_fn([query.query_text])
        query_embedding = vectors[0] if vectors else None

    hits = searcher.search(query, query_embedding=query_embedding)
    evidence = evidence_mapper(hits)
    return RetrievalResult(query=query, hits=hits, evidence=evidence)
