"""Identify likely startup points using repository evidence and labelled heuristics."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .inventory import Inventory


@dataclass(frozen=True)
class EntryPoint:
    kind: str
    location: str
    description: str
    evidence: str
    confidence: str


def _python_main_guards(path: str, text: str) -> list[EntryPoint]:
    try:
        tree = ast.parse(text, filename=path)
    except (SyntaxError, ValueError):
        return []
    results: list[EntryPoint] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        is_guard = (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and any(isinstance(op, ast.Eq) for op in test.ops)
            and any(isinstance(comp, ast.Constant) and comp.value == "__main__" for comp in test.comparators)
        )
        if is_guard:
            results.append(EntryPoint(
                kind="Python module guard",
                location=f"{path}:{node.lineno}",
                description="This file contains an if __name__ == '__main__' block, a direct-execution entry point.",
                evidence=f"{path}:{node.lineno}",
                confidence="verified syntax pattern",
            ))
    return results


def find_entrypoints(inventory: Inventory) -> list[EntryPoint]:
    entries: list[EntryPoint] = []
    for script in inventory.scripts:
        if script["source"].endswith("package.json"):
            kind = "Package script"
            desc = f"{script['command']} is declared in {script['source']} with command {script['target']}."
        else:
            kind = "Registered CLI script"
            desc = f"The {script['command']} command is registered to {script['target']} in {script['source']}."
        entries.append(EntryPoint(kind, script["source"], desc, script["source"], "manifest declaration"))

    candidates = {
        "__main__.py": "Python module execution entry point by filename convention.",
        "main.py": "Common Python application entry-point filename; execution role should be verified in its contents.",
        "cli.py": "Common command-line interface module filename; execution role should be verified in its contents.",
        "manage.py": "Common management-script filename; execution role should be verified in its contents.",
        "app.py": "Common application module filename; execution role should be verified in its contents.",
        "wsgi.py": "Common WSGI server entry-point filename; verify deployment configuration.",
        "asgi.py": "Common ASGI server entry-point filename; verify deployment configuration.",
    }
    for path, record in inventory.files.items():
        if record.suffix == ".py":
            entries.extend(_python_main_guards(path, record.text))
        name = Path(path).name.lower()
        if name in candidates:
            entries.append(EntryPoint(
                "Filename heuristic",
                path,
                candidates[name],
                path,
                "heuristic — confirm before treating as the actual startup path",
            ))

    seen: set[tuple[str, str, str]] = set()
    unique: list[EntryPoint] = []
    for entry in sorted(entries, key=lambda item: (item.location, item.kind, item.description)):
        key = (entry.kind, entry.location, entry.description)
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique[:80]
