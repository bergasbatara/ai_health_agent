import pytest

from data_ingestion import HashEmbedder, embed_chunks, embed_texts
from data_ingestion.models import PolicyChunk


def make_chunk(chunk_id: str, text: str) -> PolicyChunk:
    return PolicyChunk(
        chunk_id=chunk_id,
        document_id="aetna-knee-mri-policy",
        page_number=1,
        chunk_index=0,
        text=text,
        section_label="Knee Mri Criteria",
        study_family="knee_mri",
        retrieval_metadata={"payer_name": "Aetna"},
    )


def test_embed_texts_uses_supplied_embedder():
    embedder = HashEmbedder(dimensions=8)

    embeddings = embed_texts(["first text", "second text"], embedder=embedder)

    assert len(embeddings) == 2
    assert all(len(vector) == 8 for vector in embeddings)


def test_embed_chunks_returns_embedded_chunk_records():
    chunks = [
        make_chunk("chunk-1", "Patient completed six weeks of therapy."),
        make_chunk("chunk-2", "Prior x-ray is recommended."),
    ]

    embedded = embed_chunks(chunks, embedder=HashEmbedder(dimensions=4))

    assert len(embedded) == 2
    assert embedded[0].chunk.chunk_id == "chunk-1"
    assert len(embedded[0].embedding) == 4


def test_embed_chunks_rejects_length_mismatch():
    class BadEmbedder:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2]]

    with pytest.raises(ValueError, match="different number of embeddings"):
        embed_chunks([make_chunk("chunk-1", "text one"), make_chunk("chunk-2", "text two")], embedder=BadEmbedder())


def test_hash_embedder_is_deterministic():
    embedder = HashEmbedder(dimensions=6)

    first = embedder.embed_texts(["same text"])[0]
    second = embedder.embed_texts(["same text"])[0]

    assert first == second
