from pathlib import Path

from data_ingestion import BatchIngestionReport, HashEmbedder, InMemoryVectorStore, ingest_directory, ingest_document
from data_ingestion.models import DiscoveredPdf, RawPolicyDocument, RawPolicyPage
from domain import PayerId


def make_pdf(tmp_path: Path, filename: str, payer_id: PayerId) -> DiscoveredPdf:
    pdf_path = tmp_path / filename
    pdf_path.write_bytes(b"%PDF-1.4\nfake pdf bytes\n")
    return DiscoveredPdf(
        path=pdf_path,
        filename=filename,
        payer_id=payer_id,
        checksum_sha256="a" * 64,
    )


def fake_loader(pdf: DiscoveredPdf) -> RawPolicyDocument:
    return RawPolicyDocument(
        document_id=pdf.filename.removesuffix(".pdf").casefold().replace(" ", "-"),
        source_pdf=pdf,
        page_count=1,
        pages=[
            RawPolicyPage(
                page_number=1,
                text="KNEE MRI CRITERIA\nPatient must complete six weeks of provider-directed therapy before MRI approval.",
            )
        ],
        pdf_metadata={"Title": pdf.filename.removesuffix(".pdf")},
    )


def test_ingest_document_runs_end_to_end_with_in_memory_store(tmp_path):
    pdf = make_pdf(tmp_path, "Aetna Knee MRI policy.pdf", PayerId.AETNA)
    store = InMemoryVectorStore()

    report = ingest_document(
        pdf,
        pdf_loader=fake_loader,
        vector_store=store,
        chunk_size=8,
        overlap=2,
        embedder=HashEmbedder(dimensions=4),
    )

    assert report.document.document_id == "aetna-knee-mri-policy"
    assert report.chunk_count >= 1
    assert len(report.indexed_chunk_ids) == report.chunk_count
    assert set(report.indexed_chunk_ids) == set(store.records)


def test_ingest_directory_processes_multiple_documents(tmp_path):
    make_pdf(tmp_path, "Aetna Knee MRI policy.pdf", PayerId.AETNA)
    make_pdf(tmp_path, "Cigna_Musculoskeletal.pdf", PayerId.CIGNA)
    store = InMemoryVectorStore()

    batch_report = ingest_directory(
        str(tmp_path),
        pdf_loader=fake_loader,
        vector_store=store,
        chunk_size=8,
        overlap=2,
        embedder=HashEmbedder(dimensions=4),
    )

    assert isinstance(batch_report, BatchIngestionReport)
    assert batch_report.document_count == 2
    assert batch_report.total_chunk_count >= 2
