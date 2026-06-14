from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from data_ingestion.embedder import HashEmbedder, SentenceTransformerEmbedder
from data_ingestion.pipeline import ingest_directory
from data_ingestion.vector_store import InMemoryVectorStore
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


def run_cli(args: argparse.Namespace) -> int:
    case_path = Path(args.case_path)
    if not case_path.exists():
        raise FileNotFoundError(f"Case file does not exist: {case_path}")

    searcher = build_searcher_from_data_dir(
        args.data_dir,
        embedder_name=args.embedder,
        embedding_model=args.embedding_model,
    )
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
