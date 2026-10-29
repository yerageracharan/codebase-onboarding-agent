# Acceptance tests and current boundaries

The automated test suite is the executable acceptance suite. Run it from the repository root after installing the optional test dependency:

    python -m pip install -e ".[test]"
    python -m pytest -q

The tests use temporary synthetic repositories and mocked network/model responses. They do not run target-project code, call live GitHub, or require a paid model API.

## Covered behavior

- Local source validation and end-to-end report writing.
- Manifest parsing for supported Python, JavaScript, Rust, and Go forms.
- Python symbol extraction and entry-point candidates.
- Sensitive filenames, dotenv files, excluded directories, and common secret-pattern redaction.
- Public GitHub root URL validation, mocked archive loading, and ZIP path traversal rejection.
- Bounded source context and schema validation for model responses.
- A mocked OpenAI-compatible chat-completions response.
- Missing AI configuration handling.

## Not proven by these tests

- Live public GitHub connectivity or current GitHub service behavior.
- Compatibility with every model or provider's response quirks.
- Detection of every possible secret or prompt injection.
- Semantic understanding of arbitrary non-Python languages.
- Runtime behavior of a repository being analyzed.
- Successful setup or test execution inside a target repository.

These are explicit limitations, not implicit claims of support.
