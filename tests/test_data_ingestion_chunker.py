import pytest

from data_ingestion import build_policy_document, build_chunk_id, chunk_document, infer_section_label, split_into_word_windows
from data_ingestion.models import DiscoveredPdf, RawPolicyDocument, RawPolicyPage
from domain import PayerId


def make_raw_document(page_texts: list[str]) -> RawPolicyDocument:
    descriptor = DiscoveredPdf(
        path="/tmp/Aetna Knee MRI policy.pdf",
        filename="Aetna Knee MRI policy.pdf",
        payer_id=PayerId.AETNA,
        checksum_sha256="a" * 64,
    )
    return RawPolicyDocument(
        document_id="aetna-knee-mri-policy",
        source_pdf=descriptor,
        page_count=len(page_texts),
        pages=[RawPolicyPage(page_number=index + 1, text=text) for index, text in enumerate(page_texts)],
        pdf_metadata={"Title": "Aetna Knee MRI Policy"},
    )


def test_split_into_word_windows_applies_overlap():
    text = "one two three four five six seven eight nine ten"

    windows = split_into_word_windows(text, chunk_size=4, overlap=1)

    assert windows == [
        "one two three four",
        "four five six seven",
        "seven eight nine ten",
    ]


def test_split_into_word_windows_rejects_invalid_overlap():
    with pytest.raises(ValueError, match="overlap must be smaller than chunk_size"):
        split_into_word_windows("one two three", chunk_size=3, overlap=3)


def test_infer_section_label_from_heading_line():
    page_text = "KNEE MRI CRITERIA\nPatient must complete 6 weeks of PT."

    assert infer_section_label(page_text) == "Knee Mri Criteria"


def test_chunk_document_emits_chunk_records_with_source_metadata():
    raw_document = make_raw_document(
        [
            "KNEE MRI CRITERIA\n"
            "Patient must complete six weeks of provider-directed conservative therapy "
            "before MRI approval. Prior x-ray is recommended when clinically appropriate.",
        ]
    )
    policy_document = build_policy_document(raw_document)

    chunks = chunk_document(raw_document, policy_document, chunk_size=8, overlap=2)

    assert len(chunks) >= 2
    assert chunks[0].document_id == "aetna-knee-mri-policy"
    assert chunks[0].page_number == 1
    assert chunks[0].section_label == "Knee Mri Criteria"
    assert chunks[0].study_family == "knee_mri"
    assert chunks[0].retrieval_metadata["payer_name"] == "Aetna"


def test_build_chunk_id_is_stable():
    assert build_chunk_id("aetna-knee-mri-policy", 3, 2) == "aetna-knee-mri-policy-p3-c2"
