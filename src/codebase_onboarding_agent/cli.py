"""Command-line interface for Codebase Onboarding Agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analysis import AnalysisResult, analyze_repository
from .config import ModelConfig
from .entrypoints import find_entrypoints
from .inventory import build_inventory
from .llm import ModelError, analyze_with_model
from .report import generate_report
from .repository import RepositoryError, open_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codebase-onboard",
        description="Create a beginner-friendly, evidence-backed Markdown guide to a local or public GitHub repository.",
        epilog=(
            "Privacy: static-only mode is the default and makes no model API calls. "
            "With --with-ai, selected redacted source excerpts are sent to the endpoint you configured. "
            "The target repository is never executed."
        ),
    )
    parser.add_argument("source", help="Local repository directory or public https://github.com/OWNER/REPOSITORY URL")
    parser.add_argument("--output", "-o", default="onboarding-report.md", help="Markdown report path (default: onboarding-report.md)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--with-ai", action="store_true", help="Enhance the static report using a configured OpenAI-compatible model endpoint")
    mode.add_argument("--static-only", action="store_true", help="Run deterministic static analysis only (the default)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def run(source: str, output: Path, with_ai: bool = False) -> int:
    model_config = None
    if with_ai:
        try:
            model_config = ModelConfig.from_env()
        except ValueError as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return 2
        if model_config is None:
            print(
                "AI mode is not configured. Set CODEBASE_AGENT_BASE_URL and CODEBASE_AGENT_MODEL; "
                "CODEBASE_AGENT_API_KEY is optional for local models. See README.md.",
                file=sys.stderr,
            )
            return 2

    try:
        with open_repository(source) as (root, source_description):
            if model_config is not None:
                print("Building a bounded, redacted source inventory before calling the configured model…", file=sys.stderr)
                inventory = build_inventory(root, source_description)
                try:
                    ai = analyze_with_model(inventory, model_config)
                except ModelError as exc:
                    print(f"Model analysis failed: {exc}", file=sys.stderr)
                    return 3
                result = AnalysisResult(inventory, find_entrypoints(inventory), ai=ai, mode="AI-enhanced")
            else:
                result = analyze_repository(root, source_description)
            report = generate_report(result)
            output_path = output.expanduser().resolve()
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(report, encoding="utf-8")
            except OSError as exc:
                print(f"Could not write report to {output_path}: {exc.__class__.__name__}.", file=sys.stderr)
                return 4
            print(f"Report written: {output_path}")
            print(f"Mode: {result.mode}; files inspected: {result.inventory.file_count}; skipped: {len(result.inventory.skipped)}")
            if model_config is not None:
                print("Privacy note: selected redacted excerpts were sent to the configured model endpoint.")
            return 0
    except RepositoryError as exc:
        print(f"Repository error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Analysis error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args.source, Path(args.output), with_ai=args.with_ai)


if __name__ == "__main__":
    raise SystemExit(main())
