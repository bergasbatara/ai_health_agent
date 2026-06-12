import pytest

from data_ingestion import DiscoveredPdf, RawPolicyDocument, build_document_id, load_pdf
from domain import PayerId


def make_discovered_pdf(tmp_path, filename: str = "Aetna Knee MRI policy.pdf") -> DiscoveredPdf:
    pdf_path = tmp_path / filename
    pdf_path.write_bytes(b"%PDF-1.4\nfake pdf bytes\n")
    return DiscoveredPdf(
        path=pdf_path,
        filename=filename,
        payer_id=PayerId.AETNA,
        checksum_sha256="a" * 64,
    )


def test_build_document_id_normalizes_filename(tmp_path):
    descriptor = make_discovered_pdf(tmp_path, "Aetna Knee MRI policy.pdf")

    assert build_document_id(descriptor) == "aetna-knee-mri-policy"


def test_load_pdf_returns_page_text_and_metadata(monkeypatch, tmp_path):
    descriptor = make_discovered_pdf(tmp_path)

    class FakePage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self):
            return self._text

    class FakeReader:
        def __init__(self, path: str):
            assert path.endswith("Aetna Knee MRI policy.pdf")
            self.pages = [
                FakePage(" Page one text "),
                FakePage(None),
                FakePage("Page three text"),
            ]
            self.metadata = {"/Title": "Aetna Knee MRI policy", "/Producer": "Unit Test"}

    monkeypatch.setattr("data_ingestion.pdf_loader._load_pdf_reader", lambda: FakeReader)

    raw_document = load_pdf(descriptor)

    assert isinstance(raw_document, RawPolicyDocument)
    assert raw_document.document_id == "aetna-knee-mri-policy"
    assert raw_document.page_count == 3
    assert raw_document.pages[0].text == "Page one text"
    assert raw_document.pages[1].text == ""
    assert raw_document.pdf_metadata == {
        "Title": "Aetna Knee MRI policy",
        "Producer": "Unit Test",
    }


def test_load_pdf_raises_clear_error_when_pypdf_missing(tmp_path, monkeypatch):
    descriptor = make_discovered_pdf(tmp_path)

    def raise_import_error():
        raise ImportError("missing dependency")

    monkeypatch.setattr("data_ingestion.pdf_loader._load_pdf_reader", raise_import_error)

    with pytest.raises(ImportError, match="missing dependency"):
        load_pdf(descriptor)
