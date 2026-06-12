import hashlib

import pytest

from data_ingestion import DiscoveredPdf, compute_file_checksum, discover_pdfs, infer_payer_id
from domain import PayerId


def test_infer_payer_id_from_known_filenames():
    assert infer_payer_id("Aetna Knee MRI policy.pdf") == PayerId.AETNA
    assert infer_payer_id("Cigna_Musculoskeletal.pdf") == PayerId.CIGNA
    assert infer_payer_id("MEDADV-Rad-Card-Guidelines-June-2026.pdf") == PayerId.MEDADV


def test_infer_payer_id_defaults_to_other():
    assert infer_payer_id("some_unknown_policy.pdf") == PayerId.OTHER


def test_compute_file_checksum_matches_sha256(tmp_path):
    pdf_path = tmp_path / "example.pdf"
    pdf_bytes = b"%PDF-1.4\nfake pdf bytes\n"
    pdf_path.write_bytes(pdf_bytes)

    checksum = compute_file_checksum(pdf_path)

    assert checksum == hashlib.sha256(pdf_bytes).hexdigest()


def test_discover_pdfs_emits_sorted_descriptors_with_checksums(tmp_path):
    aetna_path = tmp_path / "Aetna Knee MRI policy.pdf"
    cigna_path = tmp_path / "Cigna_Musculoskeletal.pdf"
    note_path = tmp_path / "not_a_pdf.txt"

    aetna_path.write_bytes(b"%PDF-1.4\nAetna policy\n")
    cigna_path.write_bytes(b"%PDF-1.4\nCigna policy\n")
    note_path.write_text("ignore me")

    discovered = discover_pdfs(tmp_path)

    assert [item.filename for item in discovered] == [
        "Aetna Knee MRI policy.pdf",
        "Cigna_Musculoskeletal.pdf",
    ]
    assert all(isinstance(item, DiscoveredPdf) for item in discovered)
    assert discovered[0].payer_id == PayerId.AETNA
    assert discovered[1].payer_id == PayerId.CIGNA
    assert all(len(item.checksum_sha256) == 64 for item in discovered)


def test_discover_pdfs_raises_for_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_pdfs(tmp_path / "missing")
