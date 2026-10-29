"""Deterministic, read-only inventory of useful repository files."""

from __future__ import annotations

import ast
import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .security import is_excluded_directory, is_sensitive_path, redact_secrets

MAX_FILES_DEFAULT = 1500
MAX_FILE_BYTES_DEFAULT = 300_000
MAX_TOTAL_TEXT_BYTES_DEFAULT = 6 * 1024 * 1024
TEXT_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java",
    ".kt", ".kts", ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs",
    ".php", ".rb", ".rake", ".swift", ".scala", ".sh", ".bash", ".zsh",
    ".ps1", ".bat", ".cmd", ".sql", ".html", ".css", ".scss", ".vue", ".svelte",
    ".md", ".mdx", ".rst", ".txt", ".toml", ".json", ".yaml", ".yml", ".ini",
    ".cfg", ".conf", ".xml", ".properties", ".gradle", ".dockerfile", ".make",
    ".mk", ".tf", ".proto", ".graphql", ".gql", ".lock", ".sum", ".mod", ".gitignore",
    ".editorconfig", ".example", ".sample", ".template", ".csv",
}
_IMPORT_NAME = re.compile(r"^([A-Za-z0-9_.-]+)")


@dataclass(frozen=True)
class FileRecord:
    path: str
    size_bytes: int
    lines: int
    text: str
    suffix: str


@dataclass(frozen=True)
class PythonSymbol:
    path: str
    kind: str
    name: str
    line: int
    end_line: int
    docstring: str = ""


@dataclass
class Inventory:
    root: Path
    source_description: str
    files: dict[str, FileRecord] = field(default_factory=dict)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    symbols: list[PythonSymbol] = field(default_factory=list)
    dependencies: list[dict[str, str]] = field(default_factory=list)
    scripts: list[dict[str, str]] = field(default_factory=list)
    setup_evidence: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    readme_files: list[str] = field(default_factory=list)
    detected_languages: dict[str, int] = field(default_factory=dict)
    package_metadata: dict[str, str] = field(default_factory=dict)

    @property
    def file_count(self) -> int:
        return len(self.files)


def _is_text_candidate(path: Path) -> bool:
    name = path.name.lower()
    if name in {"dockerfile", "makefile", "justfile", "procfile", ".gitignore", ".dockerignore", ".editorconfig"}:
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def _walk_files(root: Path, max_files: int, max_file_bytes: int, max_total_bytes: int):
    count = 0
    total = 0
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(
            name for name in dirs
            if not is_excluded_directory(name) and not (current_path / name).is_symlink()
        )
        for name in sorted(names):
            path = current_path / name
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if path.is_symlink():
                yield relative, None, "symbolic link skipped"
                continue
            if is_sensitive_path(path, relative):
                yield relative, None, "sensitive file excluded"
                continue
            if not _is_text_candidate(path):
                yield relative, None, "unsupported or likely binary file type"
                continue
            try:
                stat = path.stat()
            except OSError:
                yield relative, None, "file metadata unavailable"
                continue
            if stat.st_size > max_file_bytes:
                yield relative, None, f"file exceeds {max_file_bytes} byte limit"
                continue
            if count >= max_files:
                yield relative, None, f"repository file limit ({max_files}) reached"
                continue
            if total + stat.st_size > max_total_bytes:
                yield relative, None, f"repository text budget ({max_total_bytes} bytes) reached"
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                yield relative, None, "file could not be read"
                continue
            if b"\x00" in raw[:8192]:
                yield relative, None, "binary content detected"
                continue
            text = redact_secrets(raw.decode("utf-8", errors="replace"))
            record = FileRecord(relative, stat.st_size, len(text.splitlines()), text, path.suffix.lower())
            count += 1
            total += stat.st_size
            yield relative, record, None


def _parse_python_symbols(path: str, text: str) -> list[PythonSymbol]:
    try:
        tree = ast.parse(text, filename=path)
    except (SyntaxError, ValueError):
        return []
    results: list[PythonSymbol] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else ("async function" if isinstance(node, ast.AsyncFunctionDef) else "function")
            doc = ast.get_docstring(node) or ""
            results.append(PythonSymbol(
                path=path,
                kind=kind,
                name=node.name,
                line=getattr(node, "lineno", 1),
                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                docstring=doc.splitlines()[0][:180] if doc else "",
            ))
    results.sort(key=lambda item: (item.path, item.line, item.name))
    return results


def _add_dependency(inventory: Inventory, name: str, source: str, kind: str = "declared") -> None:
    clean = name.strip()
    if not clean or clean.startswith(("#", "-e ", "--")):
        return
    key = (clean.lower(), source)
    if not any((item["name"].lower(), item["source"]) == key for item in inventory.dependencies):
        inventory.dependencies.append({"name": clean, "source": source, "kind": kind})


def _parse_manifests(inv: Inventory) -> None:
    for path, record in inv.files.items():
        if path.endswith("requirements.txt") or re.search(r"requirements[^/]*\.txt$", path, re.I):
            for line in record.text.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                match = _IMPORT_NAME.match(stripped)
                if match:
                    _add_dependency(inv, match.group(1), path)
        elif Path(path).name == "pyproject.toml":
            try:
                data = tomllib.loads(record.text)
            except tomllib.TOMLDecodeError:
                inv.skipped.append((path, "TOML could not be parsed"))
                continue
            project = data.get("project", {}) if isinstance(data.get("project", {}), dict) else {}
            if project.get("name"):
                inv.package_metadata["python_package"] = str(project["name"])
            if project.get("description"):
                inv.package_metadata["description"] = str(project["description"])
            deps = project.get("dependencies", [])
            for dep in deps if isinstance(deps, list) else []:
                _add_dependency(inv, str(dep).split(";")[0].strip(), path)
            optional = project.get("optional-dependencies", {})
            if isinstance(optional, dict):
                for group, group_deps in optional.items():
                    if isinstance(group_deps, list):
                        for dep in group_deps:
                            _add_dependency(inv, str(dep).split(";")[0].strip(), path, kind=f"optional:{group}")
            scripts = project.get("scripts", {})
            if not isinstance(scripts, dict):
                scripts = {}
            poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool", {}), dict) else {}
            if not scripts and isinstance(poetry, dict):
                scripts = poetry.get("scripts", {}) if isinstance(poetry.get("scripts", {}), dict) else {}
            for command, target in scripts.items():
                inv.scripts.append({"command": str(command), "target": str(target), "source": path})
            build_system = data.get("build-system", {})
            if isinstance(build_system, dict):
                inv.package_metadata["build_backend"] = str(build_system.get("build-backend", "declared; value not found"))
        elif Path(path).name == "package.json":
            try:
                data = json.loads(record.text)
            except json.JSONDecodeError:
                inv.skipped.append((path, "JSON could not be parsed"))
                continue
            if isinstance(data, dict):
                if data.get("name"):
                    inv.package_metadata.setdefault("javascript_package", str(data["name"]))
                for group_name in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    group = data.get(group_name, {})
                    if isinstance(group, dict):
                        for name, version in group.items():
                            _add_dependency(inv, f"{name}@{version}", path, kind=group_name)
                scripts = data.get("scripts", {})
                if isinstance(scripts, dict):
                    for name, command in scripts.items():
                        inv.scripts.append({"command": f"npm run {name}", "target": str(command), "source": path})
        elif Path(path).name == "Cargo.toml":
            try:
                data = tomllib.loads(record.text)
            except tomllib.TOMLDecodeError:
                continue
            for group_name in ("dependencies", "dev-dependencies", "build-dependencies"):
                group = data.get(group_name, {})
                if isinstance(group, dict):
                    for name in group:
                        _add_dependency(inv, str(name), path, kind=group_name)
        elif Path(path).name == "go.mod":
            for line in record.text.splitlines():
                stripped = line.strip()
                if stripped.startswith("require "):
                    _add_dependency(inv, stripped.removeprefix("require ").split()[0], path)
                elif stripped and not stripped.startswith(("//", "require", ")")) and len(stripped.split()) >= 2:
                    parts = stripped.split()
                    if parts[-1].startswith("v"):
                        _add_dependency(inv, parts[0], path)


def build_inventory(
    root: Path,
    source_description: str | None = None,
    *,
    max_files: int = MAX_FILES_DEFAULT,
    max_file_bytes: int = MAX_FILE_BYTES_DEFAULT,
    max_total_bytes: int = MAX_TOTAL_TEXT_BYTES_DEFAULT,
) -> Inventory:
    """Build an evidence inventory without executing target code."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Repository root is not a directory: {root}")
    inventory = Inventory(root=root, source_description=source_description or str(root))
    for relative, record, reason in _walk_files(root, max_files, max_file_bytes, max_total_bytes):
        if record is None:
            inventory.skipped.append((relative, reason or "skipped"))
            continue
        inventory.files[relative] = record
        suffix = record.suffix or Path(relative).name.lower()
        inventory.detected_languages[suffix] = inventory.detected_languages.get(suffix, 0) + 1
        lower = relative.lower()
        basename = Path(relative).name.lower()
        if basename.startswith("readme"):
            inventory.readme_files.append(relative)
        if "test" in Path(relative).parts or basename.startswith(("test_", "tests_")) or basename.endswith(("_test.py", ".spec.ts", ".test.ts", ".test.js")):
            inventory.test_files.append(relative)
        if record.suffix.lower() == ".py":
            inventory.symbols.extend(_parse_python_symbols(relative, record.text))
        if basename in {"readme.md", "contributing.md", "pyproject.toml", "package.json", "makefile", "justfile", "dockerfile", "requirements.txt", "go.mod", "cargo.toml"} or lower.startswith(".github/workflows/"):
            for lineno, line in enumerate(record.text.splitlines(), start=1):
                if re.search(r"\b(pip install|uv sync|poetry install|npm (?:ci|install|run)|pnpm (?:install|run)|yarn (?:install|test|build)|pytest|python -m unittest|cargo test|go test|make (?:test|check|lint))\b", line, re.I):
                    inventory.setup_evidence.append(f"{relative}:{lineno}: {line.strip()[:220]}")
    _parse_manifests(inventory)
    inventory.dependencies.sort(key=lambda item: (item["source"], item["name"].lower()))
    inventory.scripts.sort(key=lambda item: (item["source"], item["command"]))
    inventory.symbols = inventory.symbols[:400]
    inventory.test_files.sort()
    inventory.readme_files.sort()
    inventory.setup_evidence = list(dict.fromkeys(inventory.setup_evidence))[:100]
    return inventory
