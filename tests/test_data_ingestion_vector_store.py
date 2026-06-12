from data_ingestion import InMemoryVectorStore, index_embedded_chunks
from data_ingestion.models import DiscoveredPdf, EmbeddedChunk, PolicyChunk
from domain import PayerId, PolicyDocument


def make_embedded_chunk(chunk_id: str) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk=PolicyChunk(
            chunk_id=chunk_id,
            document_id="aetna-knee-mri-policy",
            page_number=1,
            chunk_index=0,
            text="Patient completed six weeks of therapy.",
            section_label="Knee Mri Criteria",
            study_family="knee_mri",
            retrieval_metadata={"payer_name": "Aetna"},
        ),
        embedding=[0.1, 0.2, 0.3],
    )


def make_policy_document() -> PolicyDocument:
    return PolicyDocument(
        document_id="aetna-knee-mri-policy",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        title="Aetna Knee MRI Policy",
        source_path="data/Aetna Knee MRI policy.pdf",
        study_family="knee_mri",
    )


def test_in_memory_vector_store_indexes_chunk_ids():
    store = InMemoryVectorStore()
    embedded_chunks = [make_embedded_chunk("chunk-1"), make_embedded_chunk("chunk-2")]

    indexed_ids = store.index_chunks(embedded_chunks)

    assert indexed_ids == ["chunk-1", "chunk-2"]
    assert set(store.records) == {"chunk-1", "chunk-2"}


def test_index_embedded_chunks_returns_ingestion_report():
    store = InMemoryVectorStore()
    embedded_chunks = [make_embedded_chunk("chunk-1")]
    report = index_embedded_chunks(embedded_chunks, make_policy_document(), vector_store=store)

    assert report.document.document_id == "aetna-knee-mri-policy"
    assert report.chunk_count == 1
    assert report.indexed_chunk_ids == ["chunk-1"]
