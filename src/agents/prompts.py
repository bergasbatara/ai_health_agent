from __future__ import annotations

import json

from .models import ExtractorInput, FormFillerInput, PolicyMatcherInput


EXTRACTOR_SYSTEM_PROMPT = """
You are a healthcare prior authorization extraction agent.
Extract structured clinical facts from the provided patient case.
Return JSON only, matching the required schema exactly.
Do not invent facts. If a fact is missing or unclear, mark it as unknown or include it in missing_facts.
""".strip()


POLICY_MATCHER_SYSTEM_PROMPT = """
You are a healthcare policy matching agent.
Compare extracted clinical facts against retrieved insurer policy evidence.
Return JSON only, matching the required schema exactly.
Every coverage conclusion must be supported by cited evidence.
Do not invent policy requirements that are not present in the evidence.
""".strip()


FORM_FILLER_SYSTEM_PROMPT = """
You are a healthcare prior authorization drafting agent.
Create a draft prior authorization artifact for human review.
Return JSON only, matching the required schema exactly.
Do not claim the request is ready if required information is missing.
Surface missing requirements and unresolved issues explicitly.
""".strip()


def _to_pretty_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def build_extractor_user_prompt(agent_input: ExtractorInput) -> str:
    patient_case = agent_input.patient_case.model_dump(mode="json")
    return (
        "Extract structured clinical facts from this patient case.\n"
        "Focus on modality, body region, laterality, symptom duration, conservative therapy, prior imaging, "
        "red flags, contraindications, diagnosis, reason for order, and missing facts.\n\n"
        f"Patient case:\n{_to_pretty_json(patient_case)}"
    )


def build_policy_matcher_user_prompt(agent_input: PolicyMatcherInput) -> str:
    payload = {
        "patient_case": agent_input.patient_case.model_dump(mode="json"),
        "extracted_facts": agent_input.extracted_facts.model_dump(mode="json"),
        "policy_evidence": [item.model_dump(mode="json") for item in agent_input.policy_evidence],
    }
    return (
        "Assess whether the extracted clinical facts satisfy the insurer policy evidence.\n"
        "Summarize key requirements, mark criteria as met/not_met/unknown/not_applicable, and cite evidence.\n\n"
        f"Inputs:\n{_to_pretty_json(payload)}"
    )


def build_form_filler_user_prompt(agent_input: FormFillerInput) -> str:
    payload = {
        "patient_case": agent_input.patient_case.model_dump(mode="json"),
        "extracted_facts": agent_input.extracted_facts.model_dump(mode="json"),
        "policy_match_result": agent_input.policy_match_result.model_dump(mode="json"),
    }
    return (
        "Draft a prior authorization output for human review using the case facts and policy match result.\n"
        "Populate form-like fields, summarize the case, and list missing requirements or unresolved issues.\n\n"
        f"Inputs:\n{_to_pretty_json(payload)}"
    )
