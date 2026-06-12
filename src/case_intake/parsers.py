from __future__ import annotations

import json

from .models import RawCaseFile, StructuredCasePayload, TextCasePayload


def parse_json_case(raw_case_file: RawCaseFile) -> StructuredCasePayload:
    if raw_case_file.file_format != "json":
        raise ValueError(f"Expected json case file, got: {raw_case_file.file_format}")

    try:
        payload = json.loads(raw_case_file.content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in case file {raw_case_file.filename}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"JSON case file must contain an object at the top level: {raw_case_file.filename}")

    known_fields = {
        "case_id",
        "payer",
        "payer_id",
        "requested_study",
        "requested_modality",
        "requested_body_region",
        "requested_laterality",
        "ordering_specialty",
        "raw_clinical_note",
        "diagnosis",
        "reason_for_order",
        "symptom_duration_weeks",
        "demographics",
        "prior_treatments",
        "prior_imaging",
    }
    additional_fields = {key: value for key, value in payload.items() if key not in known_fields}

    return StructuredCasePayload(
        case_id=payload.get("case_id"),
        payer=payload.get("payer"),
        payer_id=payload.get("payer_id"),
        requested_study=payload.get("requested_study"),
        requested_modality=payload.get("requested_modality"),
        requested_body_region=payload.get("requested_body_region"),
        requested_laterality=payload.get("requested_laterality"),
        ordering_specialty=payload.get("ordering_specialty"),
        raw_clinical_note=payload.get("raw_clinical_note"),
        diagnosis=payload.get("diagnosis"),
        reason_for_order=payload.get("reason_for_order"),
        symptom_duration_weeks=payload.get("symptom_duration_weeks"),
        demographics=payload.get("demographics") or {},
        prior_treatments=payload.get("prior_treatments") or [],
        prior_imaging=payload.get("prior_imaging") or [],
        additional_fields=additional_fields,
    )


def parse_text_case(raw_case_file: RawCaseFile) -> TextCasePayload:
    if raw_case_file.file_format != "text":
        raise ValueError(f"Expected text case file, got: {raw_case_file.file_format}")

    metadata_lines: list[str] = []
    note_lines: list[str] = []
    in_metadata = True

    for line in raw_case_file.content.splitlines():
        if in_metadata and not line.strip():
            in_metadata = False
            continue
        if in_metadata:
            metadata_lines.append(line)
        else:
            note_lines.append(line)

    metadata: dict[str, str] = {}
    for line in metadata_lines:
        if ":" not in line:
            in_metadata = False
            break
        key, value = line.split(":", 1)
        metadata[key] = value

    if not metadata:
        note_lines = raw_case_file.content.splitlines()
    elif not note_lines:
        raise ValueError(f"Text case file is missing a clinical note body: {raw_case_file.filename}")

    note_text = "\n".join(note_lines).strip()
    if not note_text:
        raise ValueError(f"Text case file is missing a clinical note body: {raw_case_file.filename}")

    return TextCasePayload(metadata=metadata, raw_clinical_note=note_text)


def parse_case_file(raw_case_file: RawCaseFile) -> StructuredCasePayload | TextCasePayload:
    if raw_case_file.file_format == "json":
        return parse_json_case(raw_case_file)
    if raw_case_file.file_format == "text":
        return parse_text_case(raw_case_file)
    raise ValueError(f"Unsupported raw case file format: {raw_case_file.file_format}")
