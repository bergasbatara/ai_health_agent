import pytest

from case_intake import RawCaseFile, StructuredCasePayload, TextCasePayload, parse_case_file, parse_json_case, parse_text_case


def test_parse_json_case_returns_structured_payload():
    raw_case = RawCaseFile(
        path="/tmp/case-001.json",
        filename="case-001.json",
        file_format="json",
        content=(
            '{"case_id":"case-001","payer":"Aetna","requested_modality":"MRI",'
            '"raw_clinical_note":"Patient has left knee pain.","custom_flag":"demo"}'
        ),
    )

    payload = parse_json_case(raw_case)

    assert isinstance(payload, StructuredCasePayload)
    assert payload.case_id == "case-001"
    assert payload.additional_fields == {"custom_flag": "demo"}


def test_parse_json_case_rejects_invalid_json():
    raw_case = RawCaseFile(
        path="/tmp/bad.json",
        filename="bad.json",
        file_format="json",
        content='{"case_id":',
    )

    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_json_case(raw_case)


def test_parse_text_case_extracts_metadata_and_note():
    raw_case = RawCaseFile(
        path="/tmp/case-002.txt",
        filename="case-002.txt",
        file_format="text",
        content="payer: Aetna\nrequested_modality: MRI\n\nPatient has persistent knee pain.",
    )

    payload = parse_text_case(raw_case)

    assert isinstance(payload, TextCasePayload)
    assert payload.metadata == {"payer": "Aetna", "requested_modality": "MRI"}
    assert payload.raw_clinical_note == "Patient has persistent knee pain."


def test_parse_text_case_without_metadata_treats_all_content_as_note():
    raw_case = RawCaseFile(
        path="/tmp/case-003.txt",
        filename="case-003.txt",
        file_format="text",
        content="Patient has persistent knee pain after six weeks of PT.",
    )

    payload = parse_text_case(raw_case)

    assert payload.metadata == {}
    assert payload.raw_clinical_note == "Patient has persistent knee pain after six weeks of PT."


def test_parse_case_file_dispatches_by_format():
    json_case = RawCaseFile(
        path="/tmp/case-001.json",
        filename="case-001.json",
        file_format="json",
        content='{"case_id":"case-001"}',
    )
    text_case = RawCaseFile(
        path="/tmp/case-002.txt",
        filename="case-002.txt",
        file_format="text",
        content="payer: Aetna\n\nPatient has persistent knee pain.",
    )

    assert isinstance(parse_case_file(json_case), StructuredCasePayload)
    assert isinstance(parse_case_file(text_case), TextCasePayload)
