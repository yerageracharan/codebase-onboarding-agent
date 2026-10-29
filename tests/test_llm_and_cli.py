from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from codebase_onboarding_agent.cli import main
from codebase_onboarding_agent.config import ModelConfig
from codebase_onboarding_agent.inventory import build_inventory
from codebase_onboarding_agent.llm import ModelError, analyze_with_model, build_context, _extract_json


def test_context_is_bounded_and_does_not_include_env(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Project\n" + "x" * 300)
    (tmp_path / ".env").write_text("API_KEY=very-secret-string-value\n")
    inv = build_inventory(tmp_path)
    context = build_context(inv)
    assert "README.md" in context
    assert ".env" not in context
    assert "very-secret-string-value" not in context


def test_model_response_schema_and_malformed_response() -> None:
    result = _extract_json('{"overview":"A small tool", "unknowns":["runtime behavior"]}')
    assert result["overview"] == "A small tool"
    assert result["unknowns"] == ["runtime behavior"]
    with pytest.raises(ModelError, match="valid JSON"):
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
    with patch("codebase_onboarding_agent.llm.urllib.request.urlopen", return_value=FakeResponse(payload)):
        actual = analyze_with_model(inv, cfg)
    assert actual["overview"] == output["overview"]


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
