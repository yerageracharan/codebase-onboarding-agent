"""Orchestrate deterministic evidence extraction and optional AI enhancement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .entrypoints import EntryPoint, find_entrypoints
from .inventory import Inventory, build_inventory


@dataclass
class AnalysisResult:
    inventory: Inventory
    entrypoints: list[EntryPoint]
    ai: dict[str, Any] | None = None
    mode: str = "static-only"


def analyze_repository(root: Path, source_description: str, ai: dict[str, Any] | None = None) -> AnalysisResult:
    inventory = build_inventory(root, source_description)
    entries = find_entrypoints(inventory)
    return AnalysisResult(inventory=inventory, entrypoints=entries, ai=ai, mode="AI-enhanced" if ai else "static-only")
