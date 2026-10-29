"""Render SVG screenshot captures from saved CLI output and generated report excerpts."""
from __future__ import annotations

import html
import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "examples" / "verification"
SHOTS = VERIFY / "screenshots"


def capture(title: str, command: str, source: str, output_name: str, limit: int = 28) -> None:
    lines: list[str] = []
    for line in source.splitlines():
        lines.extend(textwrap.wrap(line, 103, subsequent_indent="  ", break_long_words=True) if line else [""])
    omitted = max(0, len(lines) - limit)
    lines = lines[:limit]
    if omitted:
        lines[-1] = f"... {omitted} more captured lines omitted"
    height = 150 + len(lines) * 27 + 30
    text_nodes = "".join(
        f'<text x="40" y="{126 + i * 27}" class="out">{html.escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="{height}" viewBox="0 0 1440 {height}">
<rect width="1440" height="{height}" fill="#eaf0f7"/>
<rect x="18" y="18" width="1404" height="{height - 36}" rx="18" fill="#0b1728" stroke="#263b54" stroke-width="2"/>
<path d="M18 36 Q18 18 36 18 H1404 Q1422 18 1422 36 V76 H18 Z" fill="#1d2c42"/>
<circle cx="47" cy="47" r="8" fill="#ff6159"/><circle cx="74" cy="47" r="8" fill="#ffbd2e"/><circle cx="101" cy="47" r="8" fill="#28c840"/>
<text x="132" y="54" class="window">{html.escape(title)}</text>
<text x="40" y="100" class="command">$ {html.escape(command)}</text>{text_nodes}
<style>.window{{font:600 20px Arial,sans-serif;fill:#e2ebf6}}.command{{font:600 18px monospace;fill:#6ee7b7}}.out{{font:17px monospace;fill:#edf4ff}}</style></svg>'''
    (SHOTS / output_name).write_text(svg, encoding="utf-8")


def read(name: str) -> str:
    path = VERIFY / name
    return path.read_text(encoding="utf-8", errors="replace").strip() if path.exists() else f"Missing capture: {name}"


def section(report: str, heading_options: tuple[str, ...], next_heading: str | None = None) -> str:
    lines = report.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().lower() in {h.lower() for h in heading_options}), None)
    if start is None:
        return "Section heading not found in CLI-generated report: " + " / ".join(heading_options)
    end = len(lines)
    if next_heading:
        next_idx = next((i for i in range(start + 1, len(lines)) if lines[i].strip().lower() == next_heading.lower()), None)
        if next_idx is not None:
            end = next_idx
    return "\n".join(lines[start:end])


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    capture("CLI help", "codebase-onboard --help", read("02-help.txt"), "01-cli-help.svg", 28)
    capture("Analyze the included example", "codebase-onboard examples/toy-python-project --output examples/verification/toy-taskboard-report.md --static-only", read("03-toy-run.txt"), "02-analysis-command.svg", 12)
    report = read("toy-taskboard-report.md")
    capture("Generated report: overview", "Report excerpt written by the CLI", "\n".join(report.splitlines()[:35]), "03-report-overview.svg", 27)
    architecture = section(report, ("## 3. Architecture map", "## 3. Architecture and component map"), "## 4. Likely entry points")
    capture("Generated report: architecture map", "Report excerpt written by the CLI", architecture, "04-architecture-map.svg", 25)
    entries = section(report, ("## 4. Likely entry points",), "## 5. Python functions and classes")
    symbols = section(report, ("## 5. Python functions and classes",), "## 6. Dependencies and technology evidence")
    capture("Generated report: entry points and symbols", "Report excerpt written by the CLI", entries + "\n\n" + symbols, "05-entry-points-symbols.svg", 28)
    capture("Codebase Onboarding Agent tests", "python -m pytest -v", read("05-test-results.txt"), "06-agent-tests.svg", 28)
    capture("Tiny Taskboard tests", "PYTHONPATH=examples/toy-python-project/src python -m pytest -v examples/toy-python-project/tests", read("06-toy-project-tests.txt"), "07-toy-example-tests.svg", 24)
    capture("Run the Tiny Taskboard example", "PYTHONPATH=examples/toy-python-project/src python -m taskboard.cli", read("07-toy-project-run.txt"), "08-toy-example-run.svg", 12)
    capture("Invalid URL rejection", "codebase-onboard https://example.com/not-a-github-repo --static-only", read("08-invalid-url.txt"), "09-invalid-url.svg", 12)
    capture("Live public GitHub ZIP download", "codebase-onboard https://github.com/yerageracharan/codebase-onboarding-agent --static-only", read("04-live-github-run.txt"), "10-live-github-download.svg", 12)
    capture("Real model request through local Ollama", "codebase-onboard examples/toy-python-project --with-ai", read("10-ai-model-run.txt"), "11-real-model-request.svg", 12)
    ai_report = read("toy-taskboard-ai-report.md")
    ai_overview = section(ai_report, ("## AI-assisted interpretation",), "## 2. Scope and repository map")
    capture("AI-enhanced report from a real model response", "AI-assisted interpretation section", ai_overview, "12-ai-enhanced-report.svg", 28)
    metadata = [
        "# Verification run metadata", "",
        "Generated by the verification-demo workflow from the checked-out GitHub commit.",
        "Command transcripts are captured stdout/stderr. Report screenshots are excerpts from the Markdown report written by the CLI.", "",
        f"- UTC time: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Python: {os.sys.version.split()[0]}",
        f"- CLI version: {read('01-version.txt')}",
        f"- GitHub Actions run: {os.getenv('GITHUB_RUN_ID', 'local-run')}",
        f"- Source commit: {os.getenv('GITHUB_SHA', 'local working tree')}",
        "- Static-only analyzed target: examples/toy-python-project.",
        "- Live GitHub test: downloaded public repository ZIP and generated live-github-report.md, if the workflow passed.",
        "- Real model test: local Ollama qwen2.5:0.5b via OpenAI-compatible /v1/chat/completions, if the workflow passed.",
        "- AI-enhanced report: toy-taskboard-ai-report.md, produced by the CLI after a real model request.",
        "- The analyzer does not execute target code. The included synthetic example tests and CLI are run separately by this workflow.",
        "- The agent test suite and example-project tests are separate runs.",
        "- Invalid URL validation is checked without a network request.",
        "- Live GitHub ZIP download and real model-provider request are explicitly exercised in this workflow; check the recorded step outcomes.",
        "- SVG captures are rendered from actual command output/report excerpts; they are not a recording of a physical desktop session.",
        "",
    ]
    (VERIFY / "run-metadata.md").write_text("\n".join(metadata), encoding="utf-8")


if __name__ == "__main__":
    main()
