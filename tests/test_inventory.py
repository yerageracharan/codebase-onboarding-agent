from __future__ import annotations

from pathlib import Path

from codebase_onboarding_agent.analysis import analyze_repository
from codebase_onboarding_agent.entrypoints import find_entrypoints
from codebase_onboarding_agent.inventory import build_inventory
from codebase_onboarding_agent.report import generate_report


def make_project(root: Path) -> Path:
    (root / "src" / "demoapp").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "README.md").write_text("# Demo App\n\nRun it with python -m pytest.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n'
        '[project]\nname = "demo-app"\ndependencies = ["requests>=2.0"]\n'
        '[project.scripts]\ndemo-app = "demoapp.cli:main"\n', encoding="utf-8"
    )
    (root / "src" / "demoapp" / "app.py").write_text(
        '"""Example module."""\n\nclass Service:\n    """Do one job."""\n    def run(self, value: str) -> str:\n        return value.strip()\n\nif __name__ == "__main__":\n    print(Service().run(" hi "))\n', encoding="utf-8"
    )
    (root / "tests" / "test_app.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
    (root / ".env").write_text("API_KEY=super-secret-value-12345\n", encoding="utf-8")
    (root / "credentials.json").write_text('{"password": "example-secret-value"}', encoding="utf-8")
    (root / "config.py").write_text('API_KEY = "sk-abcdefghijklmnopqrstuvwxyz0123456789"\n', encoding="utf-8")
    (root / "node_modules" / "noise").mkdir(parents=True)
    (root / "node_modules" / "noise" / "index.js").write_text("no", encoding="utf-8")
    return root


def test_inventory_extracts_symbols_dependencies_scripts_and_tests(tmp_path: Path) -> None:
    root = make_project(tmp_path / "project")
    inv = build_inventory(root)
    assert inv.file_count > 0
    assert inv.package_metadata["python_package"] == "demo-app"
    assert any(dep["name"].startswith("requests") for dep in inv.dependencies)
    assert any(script["command"] == "demo-app" and script["target"] == "demoapp.cli:main" for script in inv.scripts)
    assert "tests/test_app.py" in inv.test_files
    symbol_names = {symbol.name for symbol in inv.symbols}
    assert {"Service", "run"}.issubset(symbol_names)
    assert any("README.md:3" in evidence for evidence in inv.setup_evidence)


def test_inventory_excludes_secret_files_and_redacts_secret_values(tmp_path: Path) -> None:
    root = make_project(tmp_path / "project")
    inv = build_inventory(root)
    assert ".env" not in inv.files
    assert "credentials.json" not in inv.files
    assert not any("super-secret-value-12345" in record.text for record in inv.files.values())
    assert not any("sk-abcdefghijklmnopqrstuvwxyz0123456789" in record.text for record in inv.files.values())
    assert any(path == ".env" for path, _ in inv.skipped)
    assert "node_modules/noise/index.js" not in inv.files
    assert "[REDACTED SECRET]" in inv.files["config.py"].text


def test_entrypoint_detection_uses_real_guard_and_manifest(tmp_path: Path) -> None:
    root = make_project(tmp_path / "project")
    inv = build_inventory(root)
    entries = find_entrypoints(inv)
    assert any(entry.kind == "Registered CLI script" and "demo-app" in entry.description for entry in entries)
    assert any(entry.kind == "Python module guard" and entry.location.endswith("app.py:8") for entry in entries)
    assert any(entry.kind == "Filename heuristic" and entry.location == "src/demoapp/app.py" for entry in entries)


def test_report_is_static_and_evidence_forward(tmp_path: Path) -> None:
    root = make_project(tmp_path / "project")
    report = generate_report(analyze_repository(root, str(root)))
    assert "Codebase Onboarding Report" in report
    assert "tests/test_app.py" in report
    assert "pyproject.toml" in report
    assert "No target code was executed" in report
    assert "super-secret-value-12345" not in report
    assert "sk-abcdefghijklmnopqrstuvwxyz0123456789" not in report
