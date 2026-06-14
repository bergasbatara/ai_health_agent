from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

from app.run_prior_auth import build_argument_parser, build_embedder, build_mock_crews, run_cli
from data_ingestion.embedder import HashEmbedder
from domain import ReviewStatus


def test_build_argument_parser_accepts_required_case_argument():
    parser = build_argument_parser()

    args = parser.parse_args(["--case", "case.json"])

    assert args.case_path == "case.json"
    assert args.data_dir == "data"
    assert args.embedder == "hash"
    assert args.mock_crews is False


def test_build_embedder_returns_hash_embedder_by_default():
    embedder = build_embedder("hash", "unused-model")

    assert isinstance(embedder, HashEmbedder)


def test_run_cli_invokes_workflow_with_built_dependencies(monkeypatch, tmp_path: Path, capsys):
    case_path = tmp_path / "case-001.json"
    case_path.write_text('{"case_id":"case-001","payer":"Aetna","raw_clinical_note":"note","requested_modality":"MRI","requested_body_region":"knee","requested_laterality":"left","ordering_specialty":"orthopedics"}', encoding="utf-8")

    calls: dict[str, object] = {}

    def fake_build_searcher_from_data_dir(data_dir: str, *, embedder_name: str, embedding_model: str):
        calls["data_dir"] = data_dir
        calls["embedder_name"] = embedder_name
        calls["embedding_model"] = embedding_model
        return "fake-searcher"

    def fake_build_default_crews(*, model: str | None, verbose: bool):
        calls["model"] = model
        calls["verbose"] = verbose
        return ("extractor-crew", "policy-crew", "form-crew")

    class FakeResult:
        def model_dump(self, mode: str = "python"):
            assert mode == "json"
            return {
                "workflow_id": "workflow-001",
                "status": "succeeded",
                "artifacts": {
                    "prior_auth_draft": {
                        "review_status": ReviewStatus.NEEDS_REVIEW,
                    }
                },
            }

    def fake_run_prior_auth_workflow_with_crewai(**kwargs):
        calls["workflow_kwargs"] = kwargs
        return FakeResult()

    monkeypatch.setattr("app.run_prior_auth.build_searcher_from_data_dir", fake_build_searcher_from_data_dir)
    monkeypatch.setattr("app.run_prior_auth.build_default_crews", fake_build_default_crews)
    monkeypatch.setattr("app.run_prior_auth.run_prior_auth_workflow_with_crewai", fake_run_prior_auth_workflow_with_crewai)

    args = argparse.Namespace(
        case_path=str(case_path),
        data_dir="data",
        workflow_id="workflow-001",
        model="gpt-4o-mini",
        top_k=7,
        embedder="hash",
        embedding_model="ignored",
        json_indent=2,
        verbose_crews=True,
        mock_crews=False,
    )

    exit_code = run_cli(args)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert calls["data_dir"] == "data"
    assert calls["workflow_kwargs"]["workflow_id"] == "workflow-001"
    assert calls["workflow_kwargs"]["retrieval_top_k"] == 7
    assert '"status": "succeeded"' in output


def test_build_mock_crews_supports_end_to_end_json_generation():
    extractor_crew, policy_matcher_crew, form_filler_crew = build_mock_crews()

    extractor_output = extractor_crew.kickoff(
        inputs={
            "system_prompt": "ignored",
            "user_prompt": 'Extract structured clinical facts from this patient case.\n\nPatient case:\n{"case_id":"case-001","payer_id":"aetna","payer_name":"Aetna","requested_modality":"mri","requested_body_region":"knee","requested_laterality":"left","prior_treatments":[{"completed":"yes"}],"prior_imaging":[]}',
        }
    )
    policy_output = policy_matcher_crew.kickoff(
        inputs={
            "system_prompt": "ignored",
            "user_prompt": 'Assess whether the extracted clinical facts satisfy the insurer policy evidence.\n\nInputs:\n{"patient_case":{"case_id":"case-001","payer_id":"aetna","payer_name":"Aetna","requested_modality":"mri","requested_body_region":"knee","requested_laterality":"left"},"extracted_facts":{"conservative_therapy_completed":"yes"},"policy_evidence":[{"evidence_id":"e1","document_id":"doc","chunk_id":"chunk-1","citation_text":"policy text","page_number":1}]}',
        }
    )
    form_output = form_filler_crew.kickoff(
        inputs={
            "system_prompt": "ignored",
            "user_prompt": 'Draft a prior authorization output for human review.\n\nInputs:\n{"patient_case":{"case_id":"case-001","payer_name":"Aetna","requested_modality":"mri","requested_body_region":"knee","requested_laterality":"left"},"policy_match_result":{"criteria":[{"status":"met","display_name":"Conservative therapy completed"}],"unresolved_questions":[]}}',
        }
    )

    assert '"extracted_facts"' in extractor_output.raw
    assert '"policy_match_result"' in policy_output.raw
    assert '"prior_auth_draft"' in form_output.raw


def test_run_cli_uses_mock_crews_when_requested(monkeypatch, tmp_path: Path, capsys):
    case_path = tmp_path / "case-001.json"
    case_path.write_text('{"case_id":"case-001","payer":"Aetna","raw_clinical_note":"note","requested_modality":"MRI","requested_body_region":"knee","requested_laterality":"left","ordering_specialty":"orthopedics"}', encoding="utf-8")

    calls: dict[str, object] = {}

    def fake_build_searcher_from_data_dir(data_dir: str, *, embedder_name: str, embedding_model: str):
        return "fake-searcher"

    def fake_build_mock_crews():
        calls["used_mock_crews"] = True
        return ("extractor-crew", "policy-crew", "form-crew")

    class FakeResult:
        def model_dump(self, mode: str = "python"):
            return {"workflow_id": "workflow-001", "status": "succeeded", "artifacts": {}}

    def fake_run_prior_auth_workflow_with_crewai(**kwargs):
        calls["workflow_kwargs"] = kwargs
        return FakeResult()

    monkeypatch.setattr("app.run_prior_auth.build_searcher_from_data_dir", fake_build_searcher_from_data_dir)
    monkeypatch.setattr("app.run_prior_auth.build_mock_crews", fake_build_mock_crews)
    monkeypatch.setattr("app.run_prior_auth.run_prior_auth_workflow_with_crewai", fake_run_prior_auth_workflow_with_crewai)

    args = argparse.Namespace(
        case_path=str(case_path),
        data_dir="data",
        workflow_id="workflow-001",
        model=None,
        top_k=5,
        embedder="hash",
        embedding_model="ignored",
        json_indent=2,
        verbose_crews=False,
        mock_crews=True,
    )

    exit_code = run_cli(args)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert calls["used_mock_crews"] is True
    assert calls["workflow_kwargs"]["extractor_crew"] == "extractor-crew"
    assert '"status": "succeeded"' in output
