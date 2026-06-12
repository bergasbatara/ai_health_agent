import pytest
from pydantic import ValidationError

from domain import PolicyEvidence
from retrieval import PolicySearchQuery, RetrievalResult, RetrievedChunk


def test_policy_search_query_supports_filters_and_defaults():
    query = PolicySearchQuery(
        query_text="Aetna knee MRI conservative therapy requirements",
        payer_id="aetna",
        requested_modality="mri",
        requested_body_region="knee",
        study_family="knee_mri",
    )

    assert query.top_k == 5
    assert query.payer_id == "aetna"


def test_retrieved_chunk_captures_ranked_hit_data():
    chunk = RetrievedChunk(
        chunk_id="aetna-knee-mri-p1-c0",
        document_id="aetna-knee-mri-policy",
        text="Patient must complete six weeks of conservative therapy.",
        page_number=1,
        section_label="Knee Mri Criteria",
        relevance_score=0.91,
        retrieval_metadata={"payer_name": "Aetna"},
    )

    assert chunk.page_number == 1
    assert chunk.relevance_score == 0.91


def test_retrieval_result_holds_hits_and_mapped_evidence():
    query = PolicySearchQuery(query_text="Aetna knee MRI policy", payer_id="aetna")
    hit = RetrievedChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Therapy requirement text.",
        relevance_score=0.88,
    )
    evidence = PolicyEvidence(
        evidence_id="evidence-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        citation_text="Therapy requirement text.",
        relevance_score=0.88,
    )

    result = RetrievalResult(query=query, hits=[hit], evidence=[evidence])

    assert result.query.query_text == "Aetna knee MRI policy"
    assert result.hits[0].chunk_id == "chunk-1"
    assert result.evidence[0].evidence_id == "evidence-1"


def test_retrieval_result_rejects_duplicate_evidence_ids():
    query = PolicySearchQuery(query_text="Aetna knee MRI policy")
    duplicate_evidence = [
        PolicyEvidence(
            evidence_id="evidence-1",
            document_id="doc-1",
            chunk_id="chunk-1",
            citation_text="Requirement text.",
        ),
        PolicyEvidence(
            evidence_id="evidence-1",
            document_id="doc-2",
            chunk_id="chunk-2",
            citation_text="Another requirement text.",
        ),
    ]

    with pytest.raises(ValidationError):
        RetrievalResult(query=query, evidence=duplicate_evidence)
