# Contributing

Thanks for improving Codebase Onboarding Agent. The defining property of this tool is safe, static, evidence-backed onboarding for unfamiliar codebases.

## Before changing code

- Search existing issues and commits for overlapping work.
- Open an issue before a new analysis capability, report-schema change, or architectural change. Describe the user problem, proposed behavior, alternatives, and validation plan.
- For defects, provide a minimal synthetic repository fixture, exact command, expected result, actual result, and redacted logs.
- Keep changes focused and do not combine unrelated refactors with behavior changes.

## Development setup

Python 3.11 or newer.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

## Validation

```bash
python -m pytest -q
codebase-onboard --help
python -m compileall -q src tests
```

Add fixtures for safe ZIP extraction, traversal attempts, oversized archives, secret redaction, ignored directories, manifest parsing, and evidence line locations when those boundaries change.

## Engineering expectations

- Never execute target-repository code or package installation hooks during analysis.
- Keep secret filtering and archive safety checks fail-closed.
- Clearly label heuristics and model-suggested content; do not present them as discovered facts.
- Update docs and examples when report structure or supported inputs change.
- Use synthetic credentials in tests only.

## Pull requests

Use the pull-request template. Include the problem, user impact, exact test commands/results, and any new safety assumptions. Link an issue for non-trivial work.

## Security

Do not commit sample secrets that resemble real credentials, private repository archives, access tokens, or unredacted logs. Use [SECURITY.md](SECURITY.md) for private vulnerability disclosure.
