from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from codebase_onboarding_agent.cli import main
from codebase_onboarding_agent.config import ModelConfig
from codebase_onboarding_agent.inventory import build_inventory
from codebase_onboarding_agent.llm import (
    ModelError,
    analyze_with_model,
    build_context,
    validate_model_analysis,
    _extract_json,
)


def test_context_is_bounded_and_does_not_include_env(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Project\n" + "x" * 300)
    (tmp_path / ".env").write_text("API_KEY=very-secret-string-value\n")
    inv = build_inventory(tmp_path)
    context = build_context(inv)
    assert "README.md" in context
    assert ".env" not in context
    assert "very-secret-string-value" not in context
    (tmp_path / "src" / "taskboard").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "taskboard" / "app.py").write_text("def summarize_tasks(items):\n    return len(items)\n", encoding="utf-8")
    indexed = build_inventory(tmp_path)
    indexed_context = build_context(indexed)
    assert "Readable file count: 2" in indexed_context
    assert "function summarize_tasks at src/taskboard/app.py:1-2" in indexed_context


def test_model_response_schema_and_malformed_response() -> None:
    result = _extract_json('{"overview":"A small tool", "unknowns":["runtime behavior"]}')
    assert result["overview"] == "A small tool"
    assert result["unknowns"] == ["runtime behavior"]
    wrapped = _extract_json('Here is the JSON result: {"overview":"wrapped response"} That is all.')
    assert wrapped["overview"] == "wrapped response"
    with pytest.raises(ModelError, match="not valid JSON"):
        _extract_json("this is not JSON")
    with pytest.raises(ModelError, match="JSON object"):
        _extract_json("[]")


def test_model_request_parses_openai_compatible_response(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Example project")
    inv = build_inventory(tmp_path)
    output = {"overview": "A repository with a README", "architecture_summary": "Static sources only"}
    payload = json.dumps({"choices": [{"message": {"content": json.dumps(output)}}]}).encode()

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            self.close()

    cfg = ModelConfig("http://127.0.0.1:11434/v1", "test-model")
    assert cfg.timeout_seconds == 120.0
    assert cfg.endpoint == "http://127.0.0.1:11434/v1/chat/completions"
    with patch("codebase_onboarding_agent.llm.urllib.request.urlopen", return_value=FakeResponse(payload)) as mocked_open:
        actual = analyze_with_model(inv, cfg)
    assert actual["overview"] == output["overview"]
    request = mocked_open.call_args.args[0]
    sent = json.loads(request.data.decode("utf-8"))
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["max_tokens"] == 1200


def test_grounding_filter_removes_contradictory_and_unsupported_model_claims(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "src" / "taskboard").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Tiny Taskboard\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        "[project]\nname = 'tiny-taskboard'\n", encoding="utf-8"
    )
    (project / "src" / "taskboard" / "__init__.py").write_text(
        '"""Tiny Taskboard demo package."""\n', encoding="utf-8"
    )
    (project / "src" / "taskboard" / "app.py").write_text(
        "def summarize_tasks(tasks):\n    return len(tasks)\n", encoding="utf-8"
    )
    (project / "src" / "taskboard" / "cli.py").write_text(
        "from .app import summarize_tasks\n\ndef main():\n    print(summarize_tasks([]))\n",
        encoding="utf-8",
    )
    (project / "tests" / "test_app.py").write_text(
        "from taskboard.app import summarize_tasks\n"
        "def test_empty():\n    assert summarize_tasks([]) == 0\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project)
    model_response = {
        "overview": "A tiny command-line task summary application.",
        "architecture_summary": "The source is organized in src and tests, with a declared CLI entry point.",
        "execution_walkthrough": ["Run the taskboard command after installation."],
        "notable_designs": [],
        "unknowns": [
            "The project's source code is not included in the repository; only README.md and pyproject.toml are present.",
            "The project's unit tests are not included; only tests/test_app.py is present.",
            "Runtime behavior was not executed by static analysis.",
        ],
        "contributions": [
            {
                "title": "Document package metadata",
                "path": "src/taskboard/__init__.py",
                "reason": "This file contains the project's metadata.",
                "verification": "Check the source file.",
            },
            {
                "title": "Describe the helper",
                "path": "src/taskboard/__init__.py",
                "reason": "src/taskboard/__init__.py contains the summarize_tasks function.",
                "verification": "Check the symbol location.",
            },
            {
                "title": "Change an absent module",
                "path": "src/taskboard/missing.py",
                "reason": "This module has the core logic.",
                "verification": "Run tests.",
            },
            {
                "title": "Add a focused edge-case test",
                "path": "src/taskboard/app.py",
                "reason": "Add a boundary case for summarize_tasks.",
                "verification": "Run the targeted tests.",
            },
        ],
    }

    filtered = validate_model_analysis(model_response, inventory)

    assert filtered["overview"] == model_response["overview"]
    assert filtered["architecture_summary"] == model_response["architecture_summary"]
    assert filtered["unknowns"] == ["Runtime behavior was not executed by static analysis."]
    assert [item["title"] for item in filtered["contributions"]] == ["Add a focused edge-case test"]
    assert len(filtered["_grounding_warnings"]) == 5


def test_grounding_filter_rejects_a_direct_symbol_file_mismatch(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "src" / "pkg").mkdir(parents=True)
    (project / "src" / "pkg" / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (project / "src" / "pkg" / "logic.py").write_text(
        "def summarize_tasks(items):\n    return len(items)\n", encoding="utf-8"
    )
    inventory = build_inventory(project)
    response = {
        "overview": "",
        "architecture_summary": "",
        "execution_walkthrough": [],
        "notable_designs": [],
        "unknowns": [],
        "contributions": [
            {
                "title": "Wrong symbol location",
                "path": "src/pkg/__init__.py",
                "reason": "The file src/pkg/__init__.py contains the summarize_tasks function.",
                "verification": "Check the file.",
            }
        ],
    }

    with pytest.raises(ModelError, match="All model-generated claims conflicted"):
        validate_model_analysis(response, inventory)


def test_cli_static_end_to_end_writes_report(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Tiny\n\nA synthetic project.\n")
    (project / "main.py").write_text('def main():\n    return "ok"\n\nif __name__ == "__main__":\n    main()\n')
    output = tmp_path / "out" / "report.md"
    status = main([str(project), "--output", str(output), "--static-only"])
    assert status == 0
    assert output.exists()
    contents = output.read_text()
    assert "Codebase Onboarding Report" in contents
    assert "main.py" in contents


def test_cli_ai_mode_requires_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.delenv("CODEBASE_AGENT_BASE_URL", raising=False)
    monkeypatch.delenv("CODEBASE_AGENT_MODEL", raising=False)
    monkeypatch.delenv("CODEBASE_AGENT_API_KEY", raising=False)
    status = main([str(project), "--with-ai", "--output", str(tmp_path / "never.md")])
    assert status == 2
    assert not (tmp_path / "never.md").exists()


def test_config_requires_base_url_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEBASE_AGENT_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.delenv("CODEBASE_AGENT_MODEL", raising=False)
    with pytest.raises(ValueError, match="requires both"):
        ModelConfig.from_env()
