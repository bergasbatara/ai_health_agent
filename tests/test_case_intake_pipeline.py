from pathlib import Path

from case_intake import ingest_case, ingest_case_directory
from domain import ImagingModality, PayerId


def test_ingest_case_runs_end_to_end_for_json(tmp_path: Path):
    case_path = tmp_path / "case-001.json"
    case_path.write_text(
        (
            '{"case_id":"case-001","payer":"Aetna","requested_modality":"MRI",'
            '"requested_body_region":"knee","requested_laterality":"left",'
            '"ordering_specialty":"orthopedics","raw_clinical_note":"Patient has left knee pain."}'
        ),
        encoding="utf-8",
    )

    patient_case = ingest_case(str(case_path))

    assert patient_case.case_id == "case-001"
    assert patient_case.payer_id == PayerId.AETNA
    assert patient_case.requested_modality == ImagingModality.MRI


def test_ingest_case_runs_end_to_end_for_text(tmp_path: Path):
    case_path = tmp_path / "case-002.txt"
    case_path.write_text(
        "case_id: case-002\npayer: Cigna\nrequested_modality: MRI\n\nPatient has right knee pain.",
        encoding="utf-8",
    )

    patient_case = ingest_case(str(case_path))

    assert patient_case.case_id == "case-002"
    assert patient_case.payer_id == PayerId.CIGNA
    assert patient_case.requested_body_region.value == "knee"


def test_ingest_case_directory_processes_multiple_case_files(tmp_path: Path):
    (tmp_path / "case-001.json").write_text(
        (
            '{"case_id":"case-001","payer":"Aetna","requested_modality":"MRI",'
            '"requested_body_region":"knee","raw_clinical_note":"Patient has left knee pain."}'
        ),
        encoding="utf-8",
    )
    (tmp_path / "case-002.txt").write_text(
        "case_id: case-002\npayer: Cigna\nrequested_modality: MRI\n\nPatient has right knee pain.",
        encoding="utf-8",
    )

    patient_cases = ingest_case_directory(str(tmp_path))

    assert len(patient_cases) == 2
    assert {case.case_id for case in patient_cases} == {"case-001", "case-002"}
