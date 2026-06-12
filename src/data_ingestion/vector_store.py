from __future__ import annotations

from typing import Protocol

from .models import EmbeddedChunk, IngestionReport


class VectorStore(Protocol):
    def index_chunks(self, embedded_chunks: list[EmbeddedChunk]) -> list[str]:
        ...


class InMemoryVectorStore:
    def __init__(self):
        self.records: dict[str, EmbeddedChunk] = {}

    def index_chunks(self, embedded_chunks: list[EmbeddedChunk]) -> list[str]:
        indexed_ids: list[str] = []
        for embedded_chunk in embedded_chunks:
            chunk_id = embedded_chunk.chunk.chunk_id
            self.records[chunk_id] = embedded_chunk
            indexed_ids.append(chunk_id)
        return indexed_ids


class ChromaVectorStore:
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
                    "chromadb is required for vector-store persistence. "
                    "Install dependencies with `pip install -e .` or `pip install chromadb`."
                ) from exc

            client = chromadb.PersistentClient(path=self.persist_path)
            self._collection = client.get_or_create_collection(name=self.collection_name)
        return self._collection

    def index_chunks(self, embedded_chunks: list[EmbeddedChunk]) -> list[str]:
        if not embedded_chunks:
            return []

        collection = self._load_collection()
        ids = [item.chunk.chunk_id for item in embedded_chunks]
        documents = [item.chunk.text for item in embedded_chunks]
        embeddings = [item.embedding for item in embedded_chunks]
        metadatas = [
            {
                **item.chunk.retrieval_metadata,
                "document_id": item.chunk.document_id,
                "page_number": item.chunk.page_number,
                "chunk_index": item.chunk.chunk_index,
                "section_label": item.chunk.section_label or "",
                "study_family": item.chunk.study_family,
            }
            for item in embedded_chunks
        ]
        collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return ids


def index_embedded_chunks(
    embedded_chunks: list[EmbeddedChunk],
    document,
    vector_store: VectorStore | None = None,
) -> IngestionReport:
    selected_store = vector_store or ChromaVectorStore()
    indexed_chunk_ids = selected_store.index_chunks(embedded_chunks)
    return IngestionReport(
        document=document,
        chunk_count=len(embedded_chunks),
        indexed_chunk_ids=indexed_chunk_ids,
    )
