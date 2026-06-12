from pathlib import Path

import pytest

from case_intake import discover_case_files, infer_case_file_format, load_case_file


def test_infer_case_file_format_supports_json_and_text_extensions():
    assert infer_case_file_format("case-001.json") == "json"
    assert infer_case_file_format("case-002.txt") == "text"
    assert infer_case_file_format("case-003.md") == "text"


def test_infer_case_file_format_rejects_unknown_extensions():
    with pytest.raises(ValueError, match="Unsupported case file extension"):
        infer_case_file_format("case-004.csv")


def test_load_case_file_reads_json_case(tmp_path: Path):
    case_path = tmp_path / "case-001.json"
    case_path.write_text('{"case_id": "case-001"}', encoding="utf-8")

    case_file = load_case_file(case_path)

    assert case_file.filename == "case-001.json"
    assert case_file.file_format == "json"
    assert case_file.content == '{"case_id": "case-001"}'


def test_load_case_file_reads_text_case(tmp_path: Path):
    case_path = tmp_path / "case-002.txt"
    case_path.write_text("payer: Aetna\n\nPatient has knee pain.", encoding="utf-8")

    case_file = load_case_file(case_path)

    assert case_file.file_format == "text"
    assert "payer: Aetna" in case_file.content


def test_load_case_file_rejects_empty_files(tmp_path: Path):
    case_path = tmp_path / "empty.json"
    case_path.write_text("   \n", encoding="utf-8")

    with pytest.raises(ValueError, match="Case file is empty"):
        load_case_file(case_path)


def test_discover_case_files_filters_supported_extensions(tmp_path: Path):
    (tmp_path / "case-001.json").write_text('{"case_id":"1"}', encoding="utf-8")
    (tmp_path / "case-002.txt").write_text("payer: Aetna\n\nNote", encoding="utf-8")
    (tmp_path / "ignore.csv").write_text("not,a,case", encoding="utf-8")

    case_files = discover_case_files(tmp_path)

    assert [case_file.filename for case_file in case_files] == [
        "case-001.json",
        "case-002.txt",
    ]
