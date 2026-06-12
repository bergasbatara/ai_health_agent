import pytest

from agents import AgentRuntimeError, StaticResponseProvider, parse_structured_output, run_structured_agent
from agents.models import ExtractorOutput
from domain import BodyRegion, ClinicalStatus, ImagingModality, Laterality


def valid_extractor_output_json() -> str:
    return """
    {
      "extracted_facts": {
        "case_id": "case-001",
        "requested_modality": "mri",
        "requested_body_region": "knee",
        "requested_laterality": "left",
        "symptom_duration_weeks": 8,
        "conservative_therapy_completed": "yes",
        "prior_imaging_completed": "no",
        "red_flags_present": "no",
        "contraindications_present": "unknown"
      },
      "reasoning_summary": "Structured facts extracted from the note."
    }
    """


def test_parse_structured_output_returns_typed_model():
    output = parse_structured_output(valid_extractor_output_json(), ExtractorOutput)

    assert output.extracted_facts.case_id == "case-001"
    assert output.extracted_facts.requested_modality == ImagingModality.MRI
    assert output.extracted_facts.requested_body_region == BodyRegion.KNEE
    assert output.extracted_facts.requested_laterality == Laterality.LEFT
    assert output.extracted_facts.conservative_therapy_completed == ClinicalStatus.YES


def test_parse_structured_output_rejects_invalid_json():
    with pytest.raises(AgentRuntimeError, match="not valid JSON"):
        parse_structured_output("{not-json}", ExtractorOutput)


def test_run_structured_agent_retries_until_valid_output():
    provider = StaticResponseProvider(
        responses=[
            "{bad-json}",
            valid_extractor_output_json(),
        ]
    )

    output = run_structured_agent(
        provider=provider,
        system_prompt="system",
        user_prompt="user",
        response_model=ExtractorOutput,
        max_retries=1,
    )

    assert output.reasoning_summary == "Structured facts extracted from the note."


def test_run_structured_agent_raises_after_exhausting_retries():
    provider = StaticResponseProvider(responses=["{bad-json}"])

    with pytest.raises(AgentRuntimeError, match="failed after retries"):
        run_structured_agent(
            provider=provider,
            system_prompt="system",
            user_prompt="user",
            response_model=ExtractorOutput,
            max_retries=0,
        )
