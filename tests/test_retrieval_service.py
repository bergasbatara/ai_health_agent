from data_ingestion.models import EmbeddedChunk, PolicyChunk
from domain import BodyRegion, ImagingModality, Laterality, OrderingSpecialty, PatientCase, PayerId
from retrieval import InMemoryVectorSearcher, RetrievalResult, retrieve_policy_evidence


def make_patient_case() -> PatientCase:
    return PatientCase(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        ordering_specialty=OrderingSpecialty.ORTHOPEDICS,
        raw_clinical_note="Patient has left knee pain for 8 weeks after physical therapy.",
        reason_for_order="Persistent knee pain",
        symptom_duration_weeks=8,
        prior_treatments=[{"treatment_type": "physical_therapy"}],
    )


def make_embedded_chunk(text: str, *, chunk_id: str = "chunk-1", embedding: list[float] | None = None) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk=PolicyChunk(
            chunk_id=chunk_id,
            document_id="aetna-knee-mri-policy",
            page_number=1,
            chunk_index=0,
            text=text,
            section_label="Knee Mri Criteria",
            study_family="knee_mri",
            retrieval_metadata={
                "payer_id": "aetna",
                "requested_modality": "mri",
                "requested_body_region": "knee",
                "study_family": "knee_mri",
            },
        ),
        embedding=embedding or [0.1, 0.2, 0.3],
    )


def test_retrieve_policy_evidence_returns_query_hits_and_evidence():
    patient_case = make_patient_case()
    searcher = InMemoryVectorSearcher(
        [make_embedded_chunk("Patient must complete conservative therapy before MRI approval.")]
    )

    result = retrieve_policy_evidence(patient_case, searcher=searcher, top_k=3)

    assert isinstance(result, RetrievalResult)
    assert result.query.top_k == 3
    assert len(result.hits) == 1
    assert len(result.evidence) == 1
    assert result.evidence[0].document_id == "aetna-knee-mri-policy"


def test_retrieve_policy_evidence_supports_query_embeddings():
    patient_case = make_patient_case()
    searcher = InMemoryVectorSearcher(
        [
            make_embedded_chunk("less relevant", chunk_id="chunk-1", embedding=[0.0, 1.0]),
            make_embedded_chunk("more relevant", chunk_id="chunk-2", embedding=[1.0, 0.0]),
        ]
    )

    result = retrieve_policy_evidence(
        patient_case,
        searcher=searcher,
        embed_texts_fn=lambda texts: [[1.0, 0.0]],
    )

    assert result.hits[0].chunk_id == "chunk-2"
    assert result.evidence[0].chunk_id == "chunk-2"
