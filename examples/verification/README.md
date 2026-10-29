# Reproducible CLI verification

This directory is populated by the verification workflow. It shows what the executable CLI did against the included synthetic Tiny Taskboard project.

## What was tested

1. The installed CLI help and version commands.
2. A real static-only CLI run against examples/toy-python-project, writing toy-taskboard-report.md.
3. The generated report overview, architecture map, entry points, and Python symbols.
4. The Codebase Onboarding Agent test suite, run separately from target project tests.
5. The Tiny Taskboard example's two tests and demo CLI, run separately as explicit verification steps.
6. Rejection of an invalid repository URL without a network request.

## Screenshots of the actual run

Each image below is generated from saved stdout/stderr or a section of the report written by the CLI. These are SVG screenshot-style views of the captured output rather than recordings of a physical desktop session.

### 1. CLI help

![CLI help](screenshots/01-cli-help.svg)

### 2. Run the agent against the included example

![Static analysis command output](screenshots/02-analysis-command.svg)

### 3. Generated report: overview and file map

![Generated report overview](screenshots/03-report-overview.svg)

### 4. Generated report: architecture map

![Generated architecture map](screenshots/04-architecture-map.svg)

### 5. Generated report: entry points and Python symbols

![Entry points and symbols](screenshots/05-entry-points-symbols.svg)

### 6. Codebase Onboarding Agent automated tests

![Agent test suite](screenshots/06-agent-tests.svg)

### 7. Tiny Taskboard example tests

![Synthetic example tests](screenshots/07-toy-example-tests.svg)

### 8. Run the Tiny Taskboard example CLI

![Example CLI output](screenshots/08-toy-example-run.svg)

### 9. Invalid URL handling

![Invalid URL handling](screenshots/09-invalid-url.svg)

## Evidence files

- toy-taskboard-report.md — report written by the actual codebase-onboard command.
- 01-version.txt — CLI version output.
- 02-help.txt — CLI help output.
- 03-toy-run.txt — agent CLI execution output.
- 05-test-results.txt — agent test results.
- 06-toy-project-tests.txt — example-project test results.
- 07-toy-project-run.txt — example-project runtime output.
- 08-invalid-url.txt — invalid URL validation and exit code.
- run-metadata.md — run scope and verification limits.

## Reproduce locally

From the repository root with Python 3.11 or newer:

~~~bash
python -m pip install -e ".[test]"
codebase-onboard --version
codebase-onboard --help
codebase-onboard examples/toy-python-project --output examples/verification/toy-taskboard-report.md --static-only
python -m pytest -v
PYTHONPATH=examples/toy-python-project/src python -m pytest -v examples/toy-python-project/tests
PYTHONPATH=examples/toy-python-project/src python -m taskboard.cli
python scripts/generate_verification_screenshots.py
~~~

Static-only mode does not configure or call a model. The analyzer does not execute the target repository. The sample app tests and CLI shown here are run separately by the verification workflow because Tiny Taskboard is a synthetic, included project.

## Boundaries

The workflow does not make a live public GitHub download or connect to a real model provider. Those integrations must not be described as live-verified based solely on these screenshots.
