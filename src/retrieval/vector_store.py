from __future__ import annotations

import math
import re
from typing import Any, Protocol

from data_ingestion.models import EmbeddedChunk

from .models import PolicySearchQuery, RetrievedChunk


class VectorSearcher(Protocol):
    def search(
        self,
        query: PolicySearchQuery,
        *,
        query_embedding: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        ...


def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if expected in (None, ""):
            continue
        if str(metadata.get(key)) != str(expected):
            return False
    return True


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", text.casefold()) if token}


def _keyword_score(query_text: str, document_text: str) -> float:
    query_tokens = _tokenize(query_text)
    document_tokens = _tokenize(document_text)
    if not query_tokens or not document_tokens:
        return 0.0
    overlap = query_tokens & document_tokens
    return len(overlap) / len(query_tokens)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    similarity = dot / (left_norm * right_norm)
    return max(0.0, min(1.0, similarity))


def _to_retrieved_chunk(embedded_chunk: EmbeddedChunk, relevance_score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=embedded_chunk.chunk.chunk_id,
        document_id=embedded_chunk.chunk.document_id,
        text=embedded_chunk.chunk.text,
        page_number=embedded_chunk.chunk.page_number,
        section_label=embedded_chunk.chunk.section_label,
        relevance_score=round(relevance_score, 6),
        retrieval_metadata=embedded_chunk.chunk.retrieval_metadata,
    )


class InMemoryVectorSearcher:
    def __init__(self, embedded_chunks: list[EmbeddedChunk] | None = None):
        self.records: dict[str, EmbeddedChunk] = {}
        for embedded_chunk in embedded_chunks or []:
            self.records[embedded_chunk.chunk.chunk_id] = embedded_chunk

    def add_chunks(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        for embedded_chunk in embedded_chunks:
            self.records[embedded_chunk.chunk.chunk_id] = embedded_chunk

    def search(
        self,
        query: PolicySearchQuery,
        *,
        query_embedding: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        scored_hits: list[tuple[float, EmbeddedChunk]] = []
        for embedded_chunk in self.records.values():
            if not _matches_filters(embedded_chunk.chunk.retrieval_metadata, query.filters):
                continue

            if query_embedding is not None:
                score = _cosine_similarity(query_embedding, embedded_chunk.embedding)
            else:
                score = _keyword_score(query.query_text, embedded_chunk.chunk.text)

            if score <= 0.0:
                continue
            scored_hits.append((score, embedded_chunk))

        scored_hits.sort(key=lambda item: item[0], reverse=True)
        return [
            _to_retrieved_chunk(embedded_chunk, score)
            for score, embedded_chunk in scored_hits[: query.top_k]
        ]


class ChromaVectorSearcher:
    def __init__(self, collection_name: str = "insurance_policies", persist_path: str = "./chroma_db"):
        self.collection_name = collection_name
        self.persist_path = persist_path
        self._collection = None

    def _load_collection(self):
        if self._collection is None:
            try:
                import chromadb
            except ImportError as exc:
                raise ImportError(
                    "chromadb is required for retrieval search. "
                    "Install dependencies with `pip install -e .` or `pip install chromadb`."
                ) from exc
            client = chromadb.PersistentClient(path=self.persist_path)
            self._collection = client.get_or_create_collection(name=self.collection_name)
        return self._collection

    def search(
        self,
        query: PolicySearchQuery,
        *,
        query_embedding: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        collection = self._load_collection()
        where = {key: value for key, value in query.filters.items() if value not in (None, "")}
        query_kwargs: dict[str, Any] = {
            "n_results": query.top_k,
        }
        if where:
            query_kwargs["where"] = where
        if query_embedding is not None:
            query_kwargs["query_embeddings"] = [query_embedding]
        else:
            query_kwargs["query_texts"] = [query.query_text]

        results = collection.query(**query_kwargs)
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(ids)

        hits: list[RetrievedChunk] = []
        for chunk_id, document_text, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            metadata = metadata or {}
            score = None if distance is None else max(0.0, min(1.0, 1.0 - float(distance)))
            hits.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(metadata.get("document_id", "")),
                    text=document_text,
                    page_number=metadata.get("page_number"),
                    section_label=metadata.get("section_label") or None,
                    relevance_score=score,
                    retrieval_metadata=metadata,
                )
            )
        return hits
