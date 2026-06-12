from __future__ import annotations

from typing import Callable

from domain import PatientCase

from .builders import build_patient_case
from .loaders import discover_case_files, load_case_file
from .models import NormalizedCasePayload, RawCaseFile, StructuredCasePayload, TextCasePayload
from .normalizers import normalize_case_payload
from .parsers import parse_case_file


CaseLoader = Callable[[str], RawCaseFile]
CaseParser = Callable[[RawCaseFile], StructuredCasePayload | TextCasePayload]
CaseNormalizer = Callable[[StructuredCasePayload | TextCasePayload], NormalizedCasePayload]
CaseBuilder = Callable[[NormalizedCasePayload], PatientCase]


def ingest_case(
    path: str,
    *,
    loader: CaseLoader = load_case_file,
    parser: CaseParser = parse_case_file,
    normalizer: CaseNormalizer = normalize_case_payload,
    builder: CaseBuilder = build_patient_case,
) -> PatientCase:
    raw_case_file = loader(path)
    parsed_payload = parser(raw_case_file)
    normalized_payload = normalizer(parsed_payload)
    return builder(normalized_payload)


def ingest_case_directory(
    data_dir: str,
    *,
    parser: CaseParser = parse_case_file,
    normalizer: CaseNormalizer = normalize_case_payload,
    builder: CaseBuilder = build_patient_case,
) -> list[PatientCase]:
    patient_cases: list[PatientCase] = []
    for raw_case_file in discover_case_files(data_dir):
        parsed_payload = parser(raw_case_file)
        normalized_payload = normalizer(parsed_payload)
        patient_cases.append(builder(normalized_payload))
    return patient_cases
