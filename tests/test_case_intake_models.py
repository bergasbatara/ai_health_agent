from pathlib import Path

import pytest
from pydantic import ValidationError

from case_intake import RawCaseFile, StructuredCasePayload, TextCasePayload


def test_raw_case_file_supports_json_and_text_formats():
    json_case = RawCaseFile(
        path=Path("/tmp/case-001.json"),
        filename="case-001.json",
        file_format="json",
        content='{"case_id":"case-001"}',
    )
    text_case = RawCaseFile(
        path=Path("/tmp/case-002.txt"),
        filename="case-002.txt",
        file_format="text",
        content="payer: Aetna\n\nPatient has knee pain.",
    )

    assert json_case.file_format == "json"
    assert text_case.file_format == "text"


def test_structured_case_payload_accepts_partial_case_data():
    payload = StructuredCasePayload(
        case_id="case-001",
        payer="Aetna",
        requested_modality="MRI",
        requested_body_region="knee",
        raw_clinical_note="Patient has left knee pain for 8 weeks.",
        prior_treatments=[{"treatment_type": "physical_therapy", "duration_weeks": 6}],
    )

    assert payload.case_id == "case-001"
    assert payload.prior_treatments[0]["treatment_type"] == "physical_therapy"


def test_text_case_payload_normalizes_metadata_whitespace():
    payload = TextCasePayload(
        metadata={" payer ": " Aetna ", "requested_modality": " MRI "},
        raw_clinical_note="Persistent knee pain after PT.",
    )

    assert payload.metadata == {"payer": "Aetna", "requested_modality": "MRI"}


def test_text_case_payload_rejects_blank_metadata_values():
    with pytest.raises(ValidationError):
        TextCasePayload(
            metadata={"payer": " "},
            raw_clinical_note="Persistent knee pain after PT.",
        )
