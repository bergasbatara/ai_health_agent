from datetime import date
from pathlib import Path

from data_ingestion import build_policy_document, infer_effective_date, infer_study_family, infer_version
from domain import BodyRegion, ImagingModality
from data_ingestion.models import DiscoveredPdf, RawPolicyDocument, RawPolicyPage
from domain import PayerId


def make_raw_policy_document(
    filename: str,
    payer_id: PayerId,
    page_texts: list[str],
    pdf_metadata: dict[str, str] | None = None,
) -> RawPolicyDocument:
    descriptor = DiscoveredPdf(
        path=Path("/tmp") / filename,
        filename=filename,
        payer_id=payer_id,
        checksum_sha256="a" * 64,
    )
    return RawPolicyDocument(
        document_id=filename.removesuffix(".pdf").casefold().replace(" ", "-"),
        source_pdf=descriptor,
        page_count=len(page_texts),
        pages=[RawPolicyPage(page_number=index + 1, text=text) for index, text in enumerate(page_texts)],
        pdf_metadata=pdf_metadata or {},
    )


def test_build_policy_document_for_aetna_knee_mri():
    raw_document = make_raw_policy_document(
        filename="Aetna Knee MRI policy.pdf",
        payer_id=PayerId.AETNA,
        page_texts=["Knee MRI requires 6 weeks of conservative therapy."],
        pdf_metadata={"Title": "Aetna Knee MRI Policy"},
    )

    document = build_policy_document(raw_document)

    assert document.payer_name == "Aetna"
    assert document.title == "Aetna Knee MRI Policy"
    assert document.study_family == "knee_mri"
    assert document.source_path.endswith("Aetna Knee MRI policy.pdf")


def test_infer_version_and_effective_date_from_cigna_filename_and_text():
    raw_document = make_raw_policy_document(
        filename="Cigna_Musculoskeletal Imaging Guidelines_V2.0.2025_Eff05.15.2025_pub03.28.2025upd05.23.2025.pdf",
        payer_id=PayerId.CIGNA,
        page_texts=["Cigna Musculoskeletal Imaging Guidelines V2.0.2025 Effective 05.15.2025"],
    )

    assert infer_version(raw_document) == "V2.0.2025"
    assert infer_effective_date(raw_document) == date(2025, 5, 15)


def test_infer_study_family_and_month_year_date_for_medadv():
    raw_document = make_raw_policy_document(
        filename="MEDADV-Rad-Card-Guidelines-June-2026.pdf",
        payer_id=PayerId.MEDADV,
        page_texts=["Radiology and cardiology guidelines updated June 2026."],
    )

    document = build_policy_document(raw_document)

    assert document.payer_name == "MedAdv"
    assert infer_study_family(raw_document) == "general_radiology"
    assert document.effective_date == date(2026, 6, 1)


def test_metadata_falls_back_to_filename_title_when_pdf_metadata_missing():
    raw_document = make_raw_policy_document(
        filename="unknown_policy_document.pdf",
        payer_id=PayerId.OTHER,
        page_texts=["General imaging policy."],
    )

    document = build_policy_document(raw_document)

    assert document.title == "unknown policy document"
    assert document.study_family == "general_imaging"


def test_build_policy_document_for_broad_aetna_extremity_policy():
    raw_document = make_raw_policy_document(
        filename="Magnetic Resonance Imaging (MRI) of the Extremities - Medical Clinical Policy Bulletins _ Aetna.pdf",
        payer_id=PayerId.AETNA,
        page_texts=[
            "Magnetic Resonance Imaging (MRI) of the Extremities. "
            "This Clinical Policy Bulletin addresses magnetic resonance imaging of the extremities. "
            "MRI studies of the knee when criteria are met.",
        ],
        pdf_metadata={
            "Title": "Magnetic Resonance Imaging (MRI) of the Extremities - Medical Clinical Policy Bulletins | Aetna",
        },
    )

    document = build_policy_document(raw_document)

    assert document.study_family == "extremity_mri"
    assert document.retrieval_metadata["requested_modality"] == ImagingModality.MRI
    assert document.retrieval_metadata["requested_body_region"] == BodyRegion.OTHER


def test_build_policy_document_for_broad_cigna_musculoskeletal_policy():
    raw_document = make_raw_policy_document(
        filename="Cigna_Musculoskeletal Imaging Guidelines_V2.0.2025_Eff05.15.2025.pdf",
        payer_id=PayerId.CIGNA,
        page_texts=["CIGNA MEDICAL COVERAGE POLICIES - RADIOLOGY Musculoskeletal Imaging Guidelines"],
        pdf_metadata={"Title": "Cigna Musculoskeletal Imaging Guidelines - V2.0.2025 - Effective 5/15/2025"},
    )

    document = build_policy_document(raw_document)

    assert document.study_family == "musculoskeletal_imaging"
    assert document.version == "V2.0.2025"
    assert document.effective_date == date(2025, 5, 15)
    assert document.retrieval_metadata["requested_modality"] == ImagingModality.OTHER
    assert document.retrieval_metadata["requested_body_region"] == BodyRegion.OTHER
