from agents import (
    EXTRACTOR_SYSTEM_PROMPT,
    FORM_FILLER_SYSTEM_PROMPT,
    POLICY_MATCHER_SYSTEM_PROMPT,
    ExtractorInput,
    FormFillerInput,
    PolicyMatcherInput,
    build_extractor_user_prompt,
    build_form_filler_user_prompt,
    build_policy_matcher_user_prompt,
)
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
    PolicyMatchResult,
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


def make_policy_match_result() -> PolicyMatchResult:
    evidence = PolicyEvidence(
        evidence_id="evidence-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        citation_text="MRI requires six weeks of conservative therapy.",
    )
    return PolicyMatchResult(
        case_id="case-001",
        payer_id=PayerId.AETNA,
        payer_name="Aetna",
        requested_modality=ImagingModality.MRI,
        requested_body_region=BodyRegion.KNEE,
        policy_requirements_summary="Knee MRI requires conservative treatment.",
        criteria=[
            CoverageCriterion(
                criterion_key="conservative_therapy_completed",
                display_name="Conservative therapy completed",
                status=CriterionStatus.MET,
                rationale="PT documented for 6 weeks.",
                policy_evidence=[evidence],
            )
        ],
        cited_evidence=[evidence],
    )


def test_system_prompts_are_non_empty():
    assert "JSON only" in EXTRACTOR_SYSTEM_PROMPT
    assert "cited evidence" in POLICY_MATCHER_SYSTEM_PROMPT
    assert "human review" in FORM_FILLER_SYSTEM_PROMPT


def test_build_extractor_user_prompt_includes_patient_case():
    prompt = build_extractor_user_prompt(ExtractorInput(patient_case=make_patient_case()))

    assert "Patient case" in prompt
    assert "case-001" in prompt
    assert "Persistent knee pain" in prompt


def test_build_policy_matcher_user_prompt_includes_evidence():
    prompt = build_policy_matcher_user_prompt(
        PolicyMatcherInput(
            patient_case=make_patient_case(),
            extracted_facts=make_extracted_facts(),
            policy_evidence=[
                PolicyEvidence(
                    evidence_id="evidence-1",
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    citation_text="MRI requires six weeks of conservative therapy.",
                )
            ],
        )
    )

    assert "policy_evidence" in prompt
    assert "evidence-1" in prompt


def test_build_form_filler_user_prompt_includes_policy_match_result():
    prompt = build_form_filler_user_prompt(
        FormFillerInput(
            patient_case=make_patient_case(),
            extracted_facts=make_extracted_facts(),
            policy_match_result=make_policy_match_result(),
        )
    )

    assert "policy_match_result" in prompt
    assert "Knee MRI requires conservative treatment." in prompt
