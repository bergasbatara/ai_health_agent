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


def _build_fallback_queries(query: PolicySearchQuery) -> list[PolicySearchQuery]:
    variants: list[PolicySearchQuery] = [query]
    fallback_filters = [
        {**query.filters, "study_family": None},
        {
            **query.filters,
            "study_family": None,
            "requested_body_region": None,
        },
        {
            "payer_id": query.filters.get("payer_id"),
            "requested_modality": query.filters.get("requested_modality"),
        },
        {
            "payer_id": query.filters.get("payer_id"),
        },
    ]

    seen: set[tuple[tuple[str, object], ...]] = {
        tuple(sorted((key, value) for key, value in query.filters.items() if value not in (None, "")))
    }
    for filters in fallback_filters:
        normalized_filters = {key: value for key, value in filters.items() if value not in (None, "")}
        signature = tuple(sorted(normalized_filters.items()))
        if signature in seen:
            continue
        seen.add(signature)
        variants.append(query.model_copy(update={"filters": normalized_filters}))
    return variants


def _dedupe_hits(hits: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    deduped: list[RetrievedChunk] = []
    seen_chunk_ids: set[str] = set()
    for hit in hits:
        if hit.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(hit.chunk_id)
        deduped.append(hit)
        if len(deduped) >= top_k:
            break
    return deduped


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

    hits: list[RetrievedChunk] = []
    for candidate_query in _build_fallback_queries(query):
        candidate_hits = searcher.search(candidate_query, query_embedding=query_embedding)
        hits = _dedupe_hits([*hits, *candidate_hits], query.top_k)
        if len(hits) >= query.top_k:
            break

    evidence = evidence_mapper(hits)
    return RetrievalResult(query=query, hits=hits, evidence=evidence)
