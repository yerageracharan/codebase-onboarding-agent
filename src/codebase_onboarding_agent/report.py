"""Generate a beginner-oriented Markdown report from repository evidence."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .analysis import AnalysisResult
from .entrypoints import EntryPoint
from .inventory import FileRecord, Inventory


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _model_text(value: Any, limit: int = 1800) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"<[^>]{1,500}>", "", value).strip()
    return value[:limit]


def _file_role(path: str, record: FileRecord) -> str:
    name = Path(path).name.lower()
    if name.startswith("readme"):
        return "Documentation; use it to understand the intended purpose and documented commands."
    if name == "pyproject.toml":
        return "Python package/build metadata, dependency declarations, and possible CLI registrations."
    if name == "package.json":
        return "JavaScript/Node package metadata, scripts, and dependency declarations."
    if name.startswith("requirements") and name.endswith(".txt"):
        return "Python dependency declarations; inclusion does not prove a package is used at runtime."
    if "test" in Path(path).parts or name.startswith("test_") or name.endswith(("_test.py", ".test.ts", ".spec.ts", ".test.js")):
        return "Likely test or fixture file by naming; this analyzer did not execute tests."
    if record.suffix == ".py":
        return "Python source file; see detected symbols and inspect call sites to confirm its role."
    if path.lower().startswith(".github/workflows/"):
        return "Continuous-integration or automation configuration."
    return "Readable source, configuration, or documentation; detailed role is not established by filename alone."


def _architecture(inv: Inventory, entries: list[EntryPoint]) -> str:
    manifests = [p for p in inv.files if Path(p).name.lower() in {
        "pyproject.toml", "package.json", "requirements.txt", "go.mod", "cargo.toml",
        "pom.xml", "build.gradle", "dockerfile", "makefile", "justfile",
    }]
    source_count = sum(Path(p).suffix.lower() in {
        ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs",
        ".java", ".kt", ".c", ".cpp", ".cs", ".rb", ".php", ".swift",
    } for p in inv.files)
    candidates = [e.location for e in entries[:4]]
    def select(values: list[str], fallback: str) -> str:
        return " / ".join(values[:3]) if values else fallback
    return "\n".join([
        "Structural inventory map (not a verified runtime call graph):",
        "  Repository root",
        f"    |-- Manifests/configuration: {select(manifests, 'none detected')}",
        f"    |-- Entry-point evidence: {select(candidates, 'no candidates detected')}",
        f"    |-- Readable source files: {source_count}",
        f"    |-- Likely test paths: {len(inv.test_files)}",
        f"    |-- Skipped paths: {len(inv.skipped)}",
    ])


def _ai_sections(ai: dict[str, Any]) -> list[str]:
    output = ["## AI-assisted interpretation", "", "> Model-generated from bounded, redacted excerpts. Check important claims against the cited source. No repository code or tests were executed.", ""]
    overview = _model_text(ai.get("overview"))
    architecture = _model_text(ai.get("architecture_summary"))
    if overview:
        output.extend(["### Project interpretation", "", overview, ""])
    if architecture:
        output.extend(["### Architecture summary", "", architecture, ""])
    for key, heading in (("execution_walkthrough", "Execution walkthrough"), ("notable_designs", "Design observations"), ("unknowns", "Model-reported unknowns")):
        values = ai.get(key)
        if isinstance(values, list) and values:
            output.extend([f"### {heading}", ""])
            for value in values[:10]:
                text = _model_text(value, 900) if isinstance(value, str) else ""
                if text:
                    output.append(f"- {text}")
            output.append("")
    grounding_warnings = ai.get("_grounding_warnings")
    if isinstance(grounding_warnings, list) and grounding_warnings:
        output.extend([
            "### Grounding checks",
            "",
            f"The deterministic validator removed {len(grounding_warnings)} model claim(s) that conflicted with the scanned evidence:",
            "",
        ])
        for warning in grounding_warnings[:12]:
            if isinstance(warning, str):
                output.append(f"- {_model_text(warning, 500)}")
        output.append("")
    suggestions = ai.get("contributions")
    if isinstance(suggestions, list) and suggestions:
        output.extend(["### Model-suggested contribution ideas", ""])
        for item in suggestions[:5]:
            if not isinstance(item, dict):
                continue
            title = _model_text(item.get("title"), 140) or "Suggested small change"
            path = _model_text(item.get("path"), 220)
            reason = _model_text(item.get("reason"), 400)
            verify = _model_text(item.get("verification"), 300)
            output.append(f"- **{title}**" + (f" — {path}" if path else ""))
            if reason:
                output.append(f"  - Why: {reason}")
            if verify:
                output.append(f"  - Verification idea: {verify}")
        output.append("")
    return output


def generate_report(result: AnalysisResult) -> str:
    inv = result.inventory
    entries = result.entrypoints
    out = [
        "# Codebase Onboarding Report", "",
        f"**Source:** {inv.source_description}  ",
        f"**Mode:** {result.mode}  ",
        f"**Readable files inspected:** {inv.file_count}  ",
        f"**Paths skipped:** {len(inv.skipped)}  ",
        "**Safety:** the analyzer did not execute repository source files, install scripts, or target tests.", "",
        "## 1. Thirty-second overview", "",
    ]
    if result.ai and _model_text(result.ai.get("overview")):
        out.extend([_model_text(result.ai.get("overview")), ""])
    else:
        readmes = [p for p in inv.readme_files if Path(p).name.lower() in {"readme.md", "readme.rst", "readme"}]
        manifests = [p for p in inv.files if Path(p).name.lower() in {"pyproject.toml", "package.json", "go.mod", "cargo.toml", "pom.xml", "build.gradle"}]
        out.extend([
            "Static-only mode does not guess the product purpose from the repository name.",
            "",
            "**Evidence found:** " + (", ".join(readmes[:4]) if readmes else "no conventional README detected."),
            "**Project manifests:** " + (", ".join(manifests[:8]) if manifests else "no supported manifest detected."),
            "",
        ])
    if result.ai:
        out.extend(_ai_sections(result.ai))

    out.extend([
        "## 2. Scope and repository map", "",
        f"- Source: {inv.source_description}",
        f"- Included files: {inv.file_count}",
        f"- Skipped paths: {len(inv.skipped)}",
        "- A GitHub URL is downloaded as a ZIP archive; this version does not pin a branch or commit.",
        "- Commands listed below are evidence found in source files, not commands executed by this analyzer.",
        "",
        "### Readable file tree", "",
        "    Repository root",
    ])
    for path in sorted(inv.files)[:180]:
        out.append(f"      └── {path}")
    if len(inv.files) > 180:
        out.append(f"      └── ... {len(inv.files) - 180} more readable files omitted")
    out.extend(["", "## 3. Architecture map", "",
        "This map summarizes inventory evidence only; it does not claim that every source file calls every other file.",
        "", _architecture(inv, entries), "",
    ])
    if result.ai and _model_text(result.ai.get("architecture_summary")):
        out.extend(["### Model-generated architecture explanation", "", _model_text(result.ai.get("architecture_summary")), ""])
    out.extend(["### Important files", "", "| File | Observed role or filename-based hint | Lines |", "|---|---|---:|"])
    important = []
    for path, record in inv.files.items():
        name = Path(path).name.lower()
        if name.startswith("readme") or name in {"pyproject.toml", "package.json", "requirements.txt", "go.mod", "cargo.toml", "dockerfile", "makefile", "justfile"} or path.lower().startswith(".github/workflows/"):
            important.append((path, record))
    selected = sorted(important or list(inv.files.items()))[:40]
    for path, record in selected:
        out.append(f"| {_cell(path)} | {_cell(_file_role(path, record))} | {record.lines} |")
    out.append("")

    out.extend(["## 4. Likely entry points", ""])
    if entries:
        for item in entries[:80]:
            out.append(f"- **{item.kind}:** {item.description} Evidence: {item.evidence}. Confidence: {item.confidence}.")
    else:
        out.append("No conventional entry point was identified by the supported manifest checks, Python main guards, or filename heuristics. This does not prove one is absent.")
    out.append("")

    out.extend(["## 5. Python functions and classes", ""])
    if inv.symbols:
        out.extend(["Symbols found by Python syntax-tree parsing. A symbol location does not prove that the function is called at runtime.", "", "| Symbol | File and lines | Docstring summary |", "|---|---|---|"])
        for symbol in inv.symbols[:120]:
            out.append(f"| {_cell(symbol.kind + ' ' + symbol.name)} | {_cell(f'{symbol.path}:{symbol.line}-{symbol.end_line}')} | {_cell(symbol.docstring or 'Not documented')} |")
        out.append("")
    else:
        out.extend(["No readable Python functions or classes were extracted.", ""])

    out.extend(["## 6. Dependencies and technology evidence", ""])
    if inv.package_metadata:
        out.extend(["| Metadata field | Observed value |", "|---|---|"])
        for key, value in sorted(inv.package_metadata.items()):
            out.append(f"| {_cell(key)} | {_cell(value)} |")
        out.append("")
    if inv.dependencies:
        out.extend(["| Dependency declaration | Manifest | Type |", "|---|---|---|"])
        for dep in inv.dependencies[:150]:
            out.append(f"| {_cell(dep['name'])} | {_cell(dep['source'])} | {_cell(dep['kind'])} |")
        out.append("")
        out.append("Manifest entries prove that a dependency is declared, not that the analyzer confirmed how it is used.")
    else:
        out.append("No supported dependency declarations were parsed from the inspected manifests.")
    out.append("")
    if inv.scripts:
        out.extend(["### Commands declared in manifests", "", "| Command | Configured target/value | Evidence |", "|---|---|---|"])
        for script in inv.scripts[:80]:
            out.append(f"| {_cell(script['command'])} | {_cell(script['target'])} | {_cell(script['source'])} |")
        out.append("")

    out.extend(["## 7. Setup and test-command evidence", ""])
    if inv.setup_evidence:
        out.append("The following command references were found in inspected documentation or common configuration files. They were not executed.")
        out.extend(["", *[f"- {evidence}" for evidence in inv.setup_evidence[:80]], ""])
    else:
        out.extend(["No recognized setup or test commands were found. This analyzer does not invent a command from a framework name.", ""])
    out.extend(["## 8. Detected test paths", ""])
    if inv.test_files:
        out.extend([f"Detected {len(inv.test_files)} likely test/fixture paths using naming conventions:", ""])
        out.extend(f"- {path}" for path in inv.test_files[:100])
    else:
        out.append("No obvious test paths were detected by common naming conventions. This does not prove that no tests exist.")
    out.extend(["", "A detected test file does not prove tests pass. No target test suite was run.", ""])

    out.extend(["## 9. First-contribution ideas", ""])
    suggestions = []
    for path in inv.test_files[:2]:
        suggestions.append((f"Add one narrow edge-case test for {path}", path, "Inspect existing assertions and add a single case grounded in current behavior."))
    if inv.readme_files:
        suggestions.append((f"Clarify one behavior in {inv.readme_files[0]}", inv.readme_files[0], "Cross-check the proposed wording against source before changing documentation."))
    for path, record in inv.files.items():
        if path.endswith(".py") and record.lines and len(suggestions) < 4:
            suggestions.append((f"Add a short explanation for public symbols in {path}", path, "Confirm the intended API before adding documentation."))
    if suggestions:
        for title, path, why in suggestions[:5]:
            out.extend([f"- **{title}** — {path}", f"  - Why: {why}", "  - Suggested verification: run the project's documented targeted test if appropriate; this analyzer did not run it."])
    else:
        out.append("Not enough structured evidence for file-specific suggestions. Start by locating an owner-confirmed behavior and its test.")
    out.append("")

    out.extend(["## 10. Unknowns and limitations", "",
        "- Static inspection does not prove runtime behavior or the actual call graph.",
        "- Filename-based entry-point candidates are heuristics unless supported by a manifest or Python main guard.",
        "- Setup and test commands are reported as evidence, not as verified instructions.",
        "- Secret detection is pattern-based and cannot identify every credential; review sensitive repositories before using AI mode.",
        "- Only bounded, readable text files are included. Binary, sensitive, excluded, symlinked, and oversized paths may be skipped.",
        "- AI output is an interpretation, not ground truth; verify important claims against source.",
        "",
    ])
    if inv.skipped:
        out.extend(["### Skipped paths", "", "| Path | Reason |", "|---|---|"])
        out.extend(f"| {_cell(path)} | {_cell(reason)} |" for path, reason in inv.skipped[:120])
        if len(inv.skipped) > 120:
            out.append(f"| ... | ... | {len(inv.skipped) - 120} more skipped paths omitted |")
        out.append("")
    out.extend(["## 11. Suggested next step", "",
        "Pick one supported entry point, open the cited file, and follow imports or calls into the next module. Confirm the project's own setup and test instructions before running anything.",
        "", "---", "Generated by Codebase Onboarding Agent. No target code was executed.", ""])
    return "\n".join(out)
