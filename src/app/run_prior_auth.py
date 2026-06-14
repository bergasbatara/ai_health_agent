from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from data_ingestion.embedder import HashEmbedder, SentenceTransformerEmbedder
from data_ingestion.pipeline import ingest_directory
from data_ingestion.vector_store import InMemoryVectorStore
from domain import ClinicalStatus, CriterionStatus, RecommendationSignal, ReviewStatus
from orchestration import run_prior_auth_workflow_with_crewai
from retrieval import InMemoryVectorSearcher


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the prior-authorization workflow using CrewAI crews.",
    )
    parser.add_argument("--case", required=True, dest="case_path", help="Path to the input case JSON/text file.")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing policy PDFs to ingest for retrieval. Defaults to ./data.",
    )
    parser.add_argument(
        "--workflow-id",
        default=None,
        help="Optional workflow id. Defaults to a generated id.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional CrewAI LLM identifier, for example 'gpt-4o-mini'.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of policy chunks to retrieve. Defaults to 5.",
    )
    parser.add_argument(
        "--embedder",
        choices=("hash", "sentence_transformer"),
        default="hash",
        help="Embedding backend used for policy ingestion. Defaults to 'hash'.",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name when --embedder=sentence_transformer.",
    )
    parser.add_argument(
        "--json-indent",
        type=int,
        default=2,
        help="Indentation level for JSON output. Defaults to 2.",
    )
    parser.add_argument(
        "--verbose-crews",
        action="store_true",
        help="Enable CrewAI verbose logging.",
    )
    parser.add_argument(
        "--mock-crews",
        action="store_true",
        help="Use deterministic mock crews instead of live CrewAI LLM calls.",
    )
    return parser


def build_embedder(embedder_name: str, embedding_model: str):
    if embedder_name == "hash":
        return HashEmbedder()
    if embedder_name == "sentence_transformer":
        return SentenceTransformerEmbedder(model_name=embedding_model)
    raise ValueError(f"Unsupported embedder: {embedder_name}")


def build_searcher_from_data_dir(
    data_dir: str,
    *,
    embedder_name: str = "hash",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> InMemoryVectorSearcher:
    vector_store = InMemoryVectorStore()
    ingest_directory(
        data_dir,
        vector_store=vector_store,
        embedder=build_embedder(embedder_name, embedding_model),
    )
    return InMemoryVectorSearcher(list(vector_store.records.values()))


def _extract_json_payload_from_prompt(prompt: str, marker: str) -> dict[str, Any]:
    prefix, found, suffix = prompt.partition(marker)
    if not found:
        raise ValueError(f"Prompt did not contain expected marker: {marker}")
    del prefix
    return json.loads(suffix.strip())


class _MockCrewOutput:
    def __init__(self, raw: str):
        self.raw = raw


class MockCrew:
    def __init__(self, generator):
        self._generator = generator

    def kickoff(self, inputs: dict[str, Any] | None = None) -> _MockCrewOutput:
        payload = dict(inputs or {})
        user_prompt = str(payload.get("user_prompt", ""))
        system_prompt = str(payload.get("system_prompt", ""))
        return _MockCrewOutput(self._generator(system_prompt=system_prompt, user_prompt=user_prompt))


def _build_mock_extractor_response(*, system_prompt: str, user_prompt: str) -> str:
    del system_prompt
    patient_case = _extract_json_payload_from_prompt(user_prompt, "Patient case:\n")
    prior_treatments = patient_case.get("prior_treatments", [])
    prior_imaging = patient_case.get("prior_imaging", [])
    extracted = {
        "case_id": patient_case["case_id"],
        "requested_modality": patient_case["requested_modality"],
        "requested_body_region": patient_case["requested_body_region"],
        "requested_laterality": patient_case.get("requested_laterality", "unknown"),
        "symptom_duration_weeks": patient_case.get("symptom_duration_weeks"),
        "conservative_therapy_completed": (
            ClinicalStatus.YES
            if any(item.get("completed") == ClinicalStatus.YES for item in prior_treatments)
            else ClinicalStatus.UNKNOWN
        ),
        "prior_imaging_completed": ClinicalStatus.YES if prior_imaging else ClinicalStatus.NO,
        "red_flags_present": ClinicalStatus.UNKNOWN,
        "contraindications_present": ClinicalStatus.UNKNOWN,
        "diagnosis": patient_case.get("diagnosis"),
        "reason_for_order": patient_case.get("reason_for_order"),
        "missing_facts": [],
    }
    return json.dumps(
        {
            "extracted_facts": extracted,
            "reasoning_summary": "Mock extractor converted the patient case into normalized clinical facts.",
        }
    )


def _build_mock_policy_matcher_response(*, system_prompt: str, user_prompt: str) -> str:
    del system_prompt
    payload = _extract_json_payload_from_prompt(user_prompt, "Inputs:\n")
    patient_case = payload["patient_case"]
    extracted_facts = payload["extracted_facts"]
    evidence = list(payload["policy_evidence"])
    if not evidence:
        evidence = [
            {
                "evidence_id": f"{patient_case['payer_id']}-mock-evidence-1",
                "document_id": f"{patient_case['payer_id']}-mock-policy",
                "chunk_id": "mock-chunk-1",
                "citation_text": "Mock demo mode used a synthesized policy citation because retrieval returned no direct hits.",
                "section_label": "Mock Evidence",
                "relevance_score": 0.0,
                "page_number": 1,
            }
        ]
    first_evidence = evidence[0]
    completed_therapy = extracted_facts.get("conservative_therapy_completed") == ClinicalStatus.YES
    criterion_status = CriterionStatus.MET if completed_therapy else CriterionStatus.UNKNOWN
    recommendation_signal = (
        RecommendationSignal.LIKELY_APPROVE if completed_therapy else RecommendationSignal.NEEDS_MORE_INFO
    )
    unresolved_questions = [] if completed_therapy else ["Confirm conservative therapy completion and duration."]
    return json.dumps(
        {
            "policy_match_result": {
                "case_id": patient_case["case_id"],
                "payer_id": patient_case["payer_id"],
                "payer_name": patient_case["payer_name"],
                "requested_modality": patient_case["requested_modality"],
                "requested_body_region": patient_case["requested_body_region"],
                "requested_laterality": patient_case.get("requested_laterality", "unknown"),
                "recommendation_signal": recommendation_signal,
                "policy_requirements_summary": "Mock policy matcher evaluated retrieved policy evidence for the requested study.",
                "criteria": [
                    {
                        "criterion_key": "conservative_therapy_completed",
                        "display_name": "Conservative therapy completed",
                        "status": criterion_status,
                        "rationale": (
                            "Prior physical therapy is documented in the case."
                            if completed_therapy
                            else "The case does not clearly document conservative therapy completion."
                        ),
                        "policy_evidence": [first_evidence],
                        "patient_supporting_facts": [],
                    }
                ],
                "unresolved_questions": unresolved_questions,
                "cited_evidence": evidence,
            },
            "reasoning_summary": "Mock policy matcher aligned the case facts with the retrieved policy evidence.",
        }
    )


def _build_mock_form_filler_response(*, system_prompt: str, user_prompt: str) -> str:
    del system_prompt
    payload = _extract_json_payload_from_prompt(user_prompt, "Inputs:\n")
    patient_case = payload["patient_case"]
    policy_match_result = payload["policy_match_result"]
    unresolved_issues = list(policy_match_result.get("unresolved_questions", []))
    review_status = ReviewStatus.NEEDS_REVIEW if unresolved_issues else ReviewStatus.READY_FOR_SUBMISSION
    missing_requirements = []
    for criterion in policy_match_result.get("criteria", []):
        if criterion.get("status") == CriterionStatus.NOT_MET:
            missing_requirements.append(criterion.get("display_name", criterion.get("criterion_key", "missing requirement")))
    laterality = patient_case.get("requested_laterality", "unknown")
    study_label = f"{laterality.title()} {patient_case['requested_body_region'].replace('_', ' ').title()} {patient_case['requested_modality'].upper()}"
    return json.dumps(
        {
            "prior_auth_draft": {
                "case_id": patient_case["case_id"],
                "review_status": review_status,
                "reviewer_summary": "Mock form filler prepared a draft prior-authorization artifact.",
                "form_fields": [
                    {"field_name": "requested_study", "field_value": study_label},
                    {"field_name": "payer_name", "field_value": patient_case["payer_name"]},
                ],
                "missing_requirements": missing_requirements,
                "unresolved_issues": unresolved_issues,
                "risk_flags": [],
                "submission_notes": "Generated in mock demo mode.",
            },
            "reasoning_summary": "Mock form filler populated draft fields from the policy match result.",
        }
    )


def _build_single_task_crew(
    *,
    role: str,
    goal: str,
    backstory: str,
    task_description: str,
    expected_output: str,
    model: str | None,
    verbose: bool,
):
    try:
        from crewai import Agent, Crew, Process, Task
    except ImportError as exc:
        raise ImportError(
            "CrewAI is required for this command. Install it with `pip install crewai`."
        ) from exc

    agent_kwargs: dict[str, Any] = {
        "role": role,
        "goal": goal,
        "backstory": backstory,
        "verbose": verbose,
        "allow_delegation": False,
    }
    if model:
        agent_kwargs["llm"] = model

    agent = Agent(**agent_kwargs)
    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=agent,
    )
    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=verbose,
    )


def build_default_crews(*, model: str | None = None, verbose: bool = False) -> tuple[object, object, object]:
    shared_instruction = (
        "You will receive two inputs at kickoff time: {system_prompt} and {user_prompt}.\n"
        "Treat the system prompt as binding behavior instructions and the user prompt as the task payload.\n"
        "Return only the final JSON output requested by those prompts."
    )

    extractor_crew = _build_single_task_crew(
        role="Clinical Facts Extractor",
        goal="Extract normalized clinical facts from the prior-authorization case.",
        backstory="You convert raw case material into precise structured facts without inventing details.",
        task_description=shared_instruction,
        expected_output="A JSON object matching the extractor output schema exactly.",
        model=model,
        verbose=verbose,
    )
    policy_matcher_crew = _build_single_task_crew(
        role="Policy Matcher",
        goal="Compare patient facts against retrieved insurer policy evidence.",
        backstory="You evaluate coverage criteria conservatively and support each conclusion with cited evidence.",
        task_description=shared_instruction,
        expected_output="A JSON object matching the policy matcher output schema exactly.",
        model=model,
        verbose=verbose,
    )
    form_filler_crew = _build_single_task_crew(
        role="Prior Auth Drafter",
        goal="Draft a prior-authorization submission artifact for human review.",
        backstory="You prepare complete drafts, clearly surfacing missing requirements and unresolved issues.",
        task_description=shared_instruction,
        expected_output="A JSON object matching the form filler output schema exactly.",
        model=model,
        verbose=verbose,
    )
    return extractor_crew, policy_matcher_crew, form_filler_crew


def build_mock_crews() -> tuple[object, object, object]:
    return (
        MockCrew(_build_mock_extractor_response),
        MockCrew(_build_mock_policy_matcher_response),
        MockCrew(_build_mock_form_filler_response),
    )


def run_cli(args: argparse.Namespace) -> int:
    case_path = Path(args.case_path)
    if not case_path.exists():
        raise FileNotFoundError(f"Case file does not exist: {case_path}")

    searcher = build_searcher_from_data_dir(
        args.data_dir,
        embedder_name=args.embedder,
        embedding_model=args.embedding_model,
    )
    if args.mock_crews:
        extractor_crew, policy_matcher_crew, form_filler_crew = build_mock_crews()
    else:
        extractor_crew, policy_matcher_crew, form_filler_crew = build_default_crews(
            model=args.model,
            verbose=args.verbose_crews,
        )
    workflow_id = args.workflow_id or f"prior-auth-{uuid4().hex[:12]}"
    result = run_prior_auth_workflow_with_crewai(
        workflow_id=workflow_id,
        case_path=str(case_path),
        retrieval_searcher=searcher,
        extractor_crew=extractor_crew,
        policy_matcher_crew=policy_matcher_crew,
        form_filler_crew=form_filler_crew,
        retrieval_top_k=args.top_k,
    )
    print(json.dumps(result.model_dump(mode="json"), indent=args.json_indent))
    return 0


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    return run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
