from data_ingestion.models import EmbeddedChunk, PolicyChunk
from retrieval import InMemoryVectorSearcher, PolicySearchQuery


def make_embedded_chunk(
    chunk_id: str,
    text: str,
    *,
    payer_id: str = "aetna",
    study_family: str = "knee_mri",
    embedding: list[float] | None = None,
) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk=PolicyChunk(
            chunk_id=chunk_id,
            document_id="aetna-knee-mri-policy",
            page_number=1,
            chunk_index=0,
            text=text,
            section_label="Knee Mri Criteria",
            study_family=study_family,
            retrieval_metadata={
                "payer_id": payer_id,
                "requested_modality": "mri",
                "requested_body_region": "knee",
                "study_family": study_family,
            },
        ),
        embedding=embedding or [0.1, 0.2, 0.3],
    )


def test_in_memory_vector_searcher_uses_keyword_matching_and_filters():
    searcher = InMemoryVectorSearcher(
        [
            make_embedded_chunk("chunk-1", "Patient must complete conservative therapy before MRI approval."),
            make_embedded_chunk("chunk-2", "Shoulder MRI has different criteria.", study_family="shoulder_mri"),
        ]
    )
    query = PolicySearchQuery(
        query_text="Aetna knee MRI conservative therapy",
        payer_id="aetna",
        requested_modality="mri",
        requested_body_region="knee",
        study_family="knee_mri",
        filters={
            "payer_id": "aetna",
            "requested_modality": "mri",
            "requested_body_region": "knee",
            "study_family": "knee_mri",
        },
    )

    hits = searcher.search(query)

    assert len(hits) == 1
    assert hits[0].chunk_id == "chunk-1"
    assert hits[0].relevance_score is not None


def test_in_memory_vector_searcher_supports_query_embeddings():
    searcher = InMemoryVectorSearcher(
        [
            make_embedded_chunk("chunk-1", "First chunk", embedding=[1.0, 0.0]),
            make_embedded_chunk("chunk-2", "Second chunk", embedding=[0.0, 1.0]),
        ]
    )
    query = PolicySearchQuery(query_text="ignored", filters={})

    hits = searcher.search(query, query_embedding=[1.0, 0.0])

    assert hits[0].chunk_id == "chunk-1"
    assert hits[0].relevance_score == 1.0
