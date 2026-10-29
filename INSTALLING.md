# Installing Codebase Onboarding Agent

This document describes the executable Python CLI in this repository. It is separate from the optional Agent Skill in SKILL.md.

## Requirements

- Python 3.11 or newer.
- Network access only when installing Python packages or analyzing a public GitHub repository.
- An AI model endpoint is optional. Static analysis works without an API key.

## Install from a local checkout

Clone or download this repository, open a terminal at its root, then run:

    python -m pip install -e ".[test]"

Verify the command:

    codebase-onboard --help

An alternative module invocation is:

    python -m codebase_onboarding_agent --help

## Analyze a local directory

    codebase-onboard /path/to/project --output onboarding-report.md --static-only

On Windows PowerShell, paths may look like:

    codebase-onboard "C:\Users\you\source\project" --output onboarding-report.md

## Analyze public GitHub

    codebase-onboard https://github.com/OWNER/REPOSITORY --output onboarding-report.md

Only public repository root URLs are supported by the built-in downloader. Private repositories, individual file URLs, branch URLs, and subdirectory URLs are not supported. The downloaded ZIP is limited in compressed and expanded size.

## Optional model setup

Set CODEBASE_AGENT_BASE_URL and CODEBASE_AGENT_MODEL to use an OpenAI-compatible chat-completions endpoint. CODEBASE_AGENT_API_KEY is optional for local endpoints and should be supplied only through the environment when a provider requires it.

Windows PowerShell:

    $env:CODEBASE_AGENT_BASE_URL = "http://localhost:11434/v1"
    $env:CODEBASE_AGENT_MODEL = "your-installed-model-name"
    codebase-onboard . --with-ai

macOS/Linux:

    export CODEBASE_AGENT_BASE_URL="http://localhost:11434/v1"
    export CODEBASE_AGENT_MODEL="your-installed-model-name"
    codebase-onboard . --with-ai

The model must already be available through the configured server. AI mode transmits selected redacted source excerpts to that endpoint; do not use it on confidential projects unless sharing is authorized.

## Run tests

    python -m pip install -e ".[test]"
    python -m pytest -q

The tests use synthetic repositories and mocked network/model responses. They do not run the target projects or validate live provider connectivity.
