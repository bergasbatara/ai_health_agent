from domain import PolicyEvidence
from retrieval import (
    RetrievedChunk,
    build_evidence_id,
    map_retrieved_chunk_to_policy_evidence,
    map_retrieved_chunks_to_policy_evidence,
)


def make_hit(chunk_id: str, document_id: str = "aetna-knee-mri-policy") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text="Patient must complete six weeks of conservative therapy.",
        page_number=2,
        section_label="Knee Mri Criteria",
        relevance_score=0.92,
        retrieval_metadata={"payer_name": "Aetna"},
    )


def test_build_evidence_id_is_stable():
    hit = make_hit("chunk-1")

    assert build_evidence_id(hit) == "aetna-knee-mri-policy:chunk-1"


def test_map_retrieved_chunk_to_policy_evidence_preserves_citation_fields():
    hit = make_hit("chunk-2")

    evidence = map_retrieved_chunk_to_policy_evidence(hit)

    assert isinstance(evidence, PolicyEvidence)
    assert evidence.evidence_id == "aetna-knee-mri-policy:chunk-2"
    assert evidence.document_id == "aetna-knee-mri-policy"
    assert evidence.chunk_id == "chunk-2"
    assert evidence.page_number == 2
    assert evidence.relevance_score == 0.92


def test_map_retrieved_chunks_to_policy_evidence_maps_multiple_hits():
    hits = [make_hit("chunk-1"), make_hit("chunk-2")]

    evidence = map_retrieved_chunks_to_policy_evidence(hits)

    assert len(evidence) == 2
    assert evidence[0].evidence_id == "aetna-knee-mri-policy:chunk-1"
    assert evidence[1].evidence_id == "aetna-knee-mri-policy:chunk-2"
