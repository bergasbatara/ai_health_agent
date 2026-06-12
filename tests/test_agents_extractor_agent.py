import pytest

from agents import ExtractorInput, StaticResponseProvider, run_extractor_agent
from agents.runtime import AgentRuntimeError
from domain import BodyRegion, ClinicalStatus, ImagingModality, Laterality, OrderingSpecialty, PatientCase, PayerId


def make_patient_case() -> PatientCase:
    return PatientCase(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        ordering_specialty=OrderingSpecialty.ORTHOPEDICS,
        raw_clinical_note="Patient has left knee pain for 8 weeks after PT.",
        reason_for_order="Persistent knee pain",
        symptom_duration_weeks=8,
    )


def valid_extractor_output() -> str:
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


def test_run_extractor_agent_returns_typed_output():
    agent_input = ExtractorInput(patient_case=make_patient_case())
    provider = StaticResponseProvider(responses=[valid_extractor_output()])

    output = run_extractor_agent(agent_input, provider=provider)

    assert output.extracted_facts.case_id == "case-001"
    assert output.extracted_facts.conservative_therapy_completed == ClinicalStatus.YES


def test_run_extractor_agent_raises_on_invalid_output():
    agent_input = ExtractorInput(patient_case=make_patient_case())
    provider = StaticResponseProvider(responses=["{bad-json}"])

    with pytest.raises(AgentRuntimeError):
        run_extractor_agent(agent_input, provider=provider, max_retries=0)
