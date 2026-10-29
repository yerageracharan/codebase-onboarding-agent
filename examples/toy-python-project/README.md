# Tiny Taskboard

A deliberately small command-line example that prints a task summary. This synthetic project demonstrates how Codebase Onboarding Agent grounds its explanation in files.

## Run it

Open a terminal in this folder and install the example in editable mode:

    python -m pip install -e ".[test]"

Then run the command registered in pyproject.toml:

    taskboard

To run the tests:

    python -m pytest -q

The example intentionally has no third-party runtime dependencies. The optional test dependency installs pytest. Its source uses the src layout, so install it before running the command or importing the package in tests.
