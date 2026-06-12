from __future__ import annotations

import hashlib
from typing import Protocol

from .models import EmbeddedChunk, PolicyChunk


class TextEmbedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required for embedding generation. "
                    "Install dependencies with `pip install -e .` or `pip install sentence-transformers`."
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(texts)
        return [list(map(float, embedding)) for embedding in embeddings]


class HashEmbedder:
    def __init__(self, dimensions: int = 16):
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [round(byte / 255.0, 6) for byte in digest[: self.dimensions]]
            vectors.append(vector)
        return vectors


def embed_texts(texts: list[str], embedder: TextEmbedder | None = None) -> list[list[float]]:
    selected_embedder = embedder or SentenceTransformerEmbedder()
    return selected_embedder.embed_texts(texts)


def embed_chunks(chunks: list[PolicyChunk], embedder: TextEmbedder | None = None) -> list[EmbeddedChunk]:
    if not chunks:
        return []

    vectors = embed_texts([chunk.text for chunk in chunks], embedder=embedder)
    if len(vectors) != len(chunks):
        raise ValueError("embedder returned a different number of embeddings than input chunks")

    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        embedded_chunks.append(EmbeddedChunk(chunk=chunk, embedding=vector))
    return embedded_chunks
