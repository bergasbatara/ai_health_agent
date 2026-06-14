from __future__ import annotations

from typing import Callable

from agents import ExtractorInput, FormFillerInput, PolicyMatcherInput, run_extractor_agent, run_form_filler_agent, run_policy_matcher_agent
from agents.runtime import AgentResponseProvider
from case_intake.builders import build_patient_case
from case_intake.loaders import load_case_file
from case_intake.models import NormalizedCasePayload, RawCaseFile, StructuredCasePayload, TextCasePayload
from case_intake.normalizers import normalize_case_payload
from case_intake.parsers import parse_case_file
from domain import ExtractedClinicalFacts, PatientCase, PolicyEvidence, PolicyMatchResult, PriorAuthDraft
from retrieval import RetrievedChunk, retrieve_policy_evidence
from rules_engine import evaluate_prior_auth_package

from .models import WorkflowArtifactBundle


CaseLoader = Callable[[str], RawCaseFile]
CaseParser = Callable[[RawCaseFile], StructuredCasePayload | TextCasePayload]
CaseNormalizer = Callable[[StructuredCasePayload | TextCasePayload], NormalizedCasePayload]
CaseBuilder = Callable[[NormalizedCasePayload], PatientCase]
RetrievalSearchFunction = Callable[..., list[RetrievedChunk]]


def handle_case_intake(
    case_path: str,
    *,
    loader: CaseLoader = load_case_file,
    parser: CaseParser = parse_case_file,
    normalizer: CaseNormalizer = normalize_case_payload,
    builder: CaseBuilder = build_patient_case,
) -> WorkflowArtifactBundle:
    raw_case_file = loader(case_path)
    parsed_payload = parser(raw_case_file)
    normalized_payload = normalizer(parsed_payload)
    patient_case = builder(normalized_payload)
    return WorkflowArtifactBundle(
        raw_case_file=raw_case_file,
        patient_case=patient_case,
    )


def handle_fact_extraction(
    patient_case: PatientCase,
    *,
    provider: AgentResponseProvider,
    max_retries: int = 1,
) -> WorkflowArtifactBundle:
    extractor_output = run_extractor_agent(
        ExtractorInput(patient_case=patient_case),
        provider=provider,
        max_retries=max_retries,
    )
    return WorkflowArtifactBundle(
        patient_case=patient_case,
        extractor_output=extractor_output,
        extracted_facts=extractor_output.extracted_facts,
    )


def handle_policy_retrieval(
    patient_case: PatientCase,
    *,
    searcher,
    top_k: int = 5,
    embed_texts_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> WorkflowArtifactBundle:
    retrieval_result = retrieve_policy_evidence(
        patient_case,
        searcher=searcher,
        top_k=top_k,
        embed_texts_fn=embed_texts_fn,
    )
    return WorkflowArtifactBundle(
        patient_case=patient_case,
        retrieval_result=retrieval_result,
    )


def handle_policy_matching(
    patient_case: PatientCase,
    extracted_facts: ExtractedClinicalFacts,
    policy_evidence: list[PolicyEvidence],
    *,
    provider: AgentResponseProvider,
    max_retries: int = 1,
) -> WorkflowArtifactBundle:
    policy_matcher_output = run_policy_matcher_agent(
        PolicyMatcherInput(
            patient_case=patient_case,
            extracted_facts=extracted_facts,
            policy_evidence=policy_evidence,
        ),
        provider=provider,
        max_retries=max_retries,
    )
    return WorkflowArtifactBundle(
        patient_case=patient_case,
        extracted_facts=extracted_facts,
        policy_matcher_output=policy_matcher_output,
        policy_match_result=policy_matcher_output.policy_match_result,
    )


def handle_draft_generation(
    patient_case: PatientCase,
    extracted_facts: ExtractedClinicalFacts,
    policy_match_result: PolicyMatchResult,
    *,
    provider: AgentResponseProvider,
    max_retries: int = 1,
) -> WorkflowArtifactBundle:
    form_filler_output = run_form_filler_agent(
        FormFillerInput(
            patient_case=patient_case,
            extracted_facts=extracted_facts,
            policy_match_result=policy_match_result,
        ),
        provider=provider,
        max_retries=max_retries,
    )
    return WorkflowArtifactBundle(
        patient_case=patient_case,
        extracted_facts=extracted_facts,
        policy_match_result=policy_match_result,
        form_filler_output=form_filler_output,
        prior_auth_draft=form_filler_output.prior_auth_draft,
    )


def handle_rules_validation(
    patient_case: PatientCase,
    extracted_facts: ExtractedClinicalFacts,
    policy_match_result: PolicyMatchResult,
    prior_auth_draft: PriorAuthDraft,
) -> WorkflowArtifactBundle:
    rules_result = evaluate_prior_auth_package(
        patient_case,
        extracted_facts,
        policy_match_result,
        prior_auth_draft,
    )
    return WorkflowArtifactBundle(
        patient_case=patient_case,
        extracted_facts=extracted_facts,
        policy_match_result=policy_match_result,
        prior_auth_draft=prior_auth_draft,
        rules_result=rules_result,
    )
