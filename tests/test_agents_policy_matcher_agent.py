import pytest

from agents import PolicyMatcherInput, StaticResponseProvider, run_policy_matcher_agent
from agents.runtime import AgentRuntimeError
from domain import (
    BodyRegion,
    ClinicalStatus,
    CoverageCriterion,
    CriterionStatus,
    ExtractedClinicalFacts,
    ImagingModality,
    Laterality,
    OrderingSpecialty,
    PatientCase,
    PayerId,
    PolicyEvidence,
)


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


def make_extracted_facts() -> ExtractedClinicalFacts:
    return ExtractedClinicalFacts(
        case_id="case-001",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        requested_laterality=Laterality.LEFT,
        symptom_duration_weeks=8,
        conservative_therapy_completed=ClinicalStatus.YES,
        prior_imaging_completed=ClinicalStatus.NO,
        red_flags_present=ClinicalStatus.NO,
        contraindications_present=ClinicalStatus.UNKNOWN,
    )


def make_policy_evidence() -> PolicyEvidence:
    return PolicyEvidence(
        evidence_id="evidence-1",
        document_id="aetna-knee-mri-policy",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
        section_label="Knee Mri Criteria",
        relevance_score=0.91,
        page_number=2,
    )


def valid_policy_matcher_output() -> str:
    return """
    {
      "policy_match_result": {
        "case_id": "case-001",
        "payer_id": "aetna",
        "payer_name": "Aetna",
        "requested_modality": "mri",
        "requested_body_region": "knee",
        "requested_laterality": "left",
        "policy_requirements_summary": "Knee MRI requires conservative therapy before approval.",
        "criteria": [
          {
            "criterion_key": "conservative_therapy_completed",
            "display_name": "Conservative therapy completed",
            "status": "met",
            "rationale": "The note documents 6 weeks of PT.",
            "policy_evidence": [
              {
                "evidence_id": "evidence-1",
                "document_id": "aetna-knee-mri-policy",
                "chunk_id": "chunk-1",
                "citation_text": "MRI requires six weeks of conservative therapy.",
                "section_label": "Knee Mri Criteria",
                "relevance_score": 0.91,
                "page_number": 2
              }
            ]
          }
        ],
        "cited_evidence": [
          {
            "evidence_id": "evidence-1",
            "document_id": "aetna-knee-mri-policy",
            "chunk_id": "chunk-1",
            "citation_text": "MRI requires six weeks of conservative therapy.",
            "section_label": "Knee Mri Criteria",
            "relevance_score": 0.91,
            "page_number": 2
          }
        ]
      },
      "reasoning_summary": "Policy evidence supports that conservative therapy is documented."
    }
    """


def test_run_policy_matcher_agent_returns_typed_output():
    agent_input = PolicyMatcherInput(
        patient_case=make_patient_case(),
        extracted_facts=make_extracted_facts(),
        policy_evidence=[make_policy_evidence()],
    )
    provider = StaticResponseProvider(responses=[valid_policy_matcher_output()])

    output = run_policy_matcher_agent(agent_input, provider=provider)

    assert output.policy_match_result.case_id == "case-001"
    assert output.policy_match_result.cited_evidence[0].evidence_id == "evidence-1"
    assert output.policy_match_result.criteria[0].status == CriterionStatus.MET


def test_run_policy_matcher_agent_raises_on_invalid_output():
    agent_input = PolicyMatcherInput(
        patient_case=make_patient_case(),
        extracted_facts=make_extracted_facts(),
        policy_evidence=[make_policy_evidence()],
    )
    provider = StaticResponseProvider(responses=["{bad-json}"])

    with pytest.raises(AgentRuntimeError):
        run_policy_matcher_agent(agent_input, provider=provider, max_retries=0)
