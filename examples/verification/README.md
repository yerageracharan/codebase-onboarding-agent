# Reproducible CLI verification

This directory is populated by the verification workflow. It tests the executable CLI against the included synthetic Tiny Taskboard project and the live public GitHub repository.

## What is tested

1. Installed CLI help and version commands.
2. Static-only analysis of the included Tiny Taskboard project.
3. Live public GitHub ZIP download of this repository, followed by static report generation.
4. The Codebase Onboarding Agent test suite.
5. Tiny Taskboard's two tests and demo CLI, run separately from analysis.
6. A real AI request to a locally hosted Ollama model (qwen2.5:1.5b) through the OpenAI-compatible /v1/chat/completions endpoint.
7. Validation of the AI-enhanced report from that request.
8. Invalid repository URL rejection without a network request.

## Screenshots of the actual run

Each image is rendered from saved stdout/stderr or excerpts of the report files the CLI wrote. Terminal-style captures are not recordings of a physical desktop session.

### 1. CLI help

![CLI help](screenshots/01-cli-help.svg)

### 2. Analyze the included toy project

![Static analysis command output](screenshots/02-analysis-command.svg)

### 3. Generated static report: overview

![Generated report overview](screenshots/03-report-overview.svg)

### 4. Generated static report: architecture map

![Generated architecture map](screenshots/04-architecture-map.svg)

### 5. Generated report: entry points and Python symbols

![Entry points and symbols](screenshots/05-entry-points-symbols.svg)

### 6. Agent tests

![Agent tests](screenshots/06-agent-tests.svg)

### 7. Tiny Taskboard tests

![Toy example tests](screenshots/07-toy-example-tests.svg)

### 8. Run the toy application

![Example CLI output](screenshots/08-toy-example-run.svg)

### 9. Invalid URL handling

![Invalid URL handling](screenshots/09-invalid-url.svg)

### 10. Live public GitHub ZIP download

![Live GitHub download](screenshots/10-live-github-download.svg)

### 11. Real AI request through local Ollama

![Real model request](screenshots/11-real-model-request.svg)

### 12. AI-enhanced report produced by that request

![AI-enhanced report](screenshots/12-ai-enhanced-report.svg)

## Evidence files

- toy-taskboard-report.md — static report written from the included project.
- live-github-report.md — report written after downloading the public repository archive.
- toy-taskboard-ai-report.md — report produced with a real Ollama model request.
- 01-version.txt and 02-help.txt — CLI output.
- 03-toy-run.txt, 04-live-github-run.txt, 10-ai-model-run.txt — actual CLI run summaries.
- 05-test-results.txt — agent test results.
- 06-toy-project-tests.txt and 07-toy-project-run.txt — separate sample tests and runtime output.
- 08-invalid-url.txt — validation error and exit code.
- 09-ollama-model.txt — provider/model/endpoint details.
- run-metadata.md — run scope and limits.

## Reproduce locally

Python 3.11 or newer is required. To reproduce live AI testing, install Ollama and download the same model first; that setup is optional for static use.

~~~bash
python -m pip install -e ".[test]"
codebase-onboard examples/toy-python-project --output examples/verification/toy-taskboard-report.md --static-only
python -m pytest -v
PYTHONPATH=examples/toy-python-project/src python -m pytest -v examples/toy-python-project/tests
PYTHONPATH=examples/toy-python-project/src python -m taskboard.cli
codebase-onboard https://github.com/yerageracharan/codebase-onboarding-agent --output examples/verification/live-github-report.md --static-only
ollama serve
ollama pull qwen2.5:1.5b
CODEBASE_AGENT_BASE_URL=http://127.0.0.1:11434/v1 CODEBASE_AGENT_MODEL=qwen2.5:1.5b codebase-onboard examples/toy-python-project --with-ai --output examples/verification/toy-taskboard-ai-report.md
python scripts/generate_verification_screenshots.py
~~~

The analyzer does not execute target source. Sample project tests and its runtime command are separate verification steps. Live GitHub testing requires network access; AI testing downloads/runs the selected local model.

## Verification boundaries

A passing GitHub step verifies the current ZIP downloader against this public repository at run time, not every public repository or private repositories. A passing Ollama step verifies the request path with the tested model only; it does not imply every hosted provider or model is compatible.
