# Examples index

The examples are separated by purpose. The included Tiny Taskboard project is a synthetic fixture; it is not a production application or a third-party repository.

| Path | Tag | What it contains |
|---|---|---|
| [toy-python-project/](toy-python-project/) | `Synthetic project` | Small Python CLI with a `pyproject.toml`, source modules and two unit tests. Use it to understand report output or reproduce the documented example. |
| [reports/sample-onboarding-report.md](reports/sample-onboarding-report.md) | `Sample output` | Curated, evidence-backed example report based on Tiny Taskboard. |
| [verification/](verification/) | `Live run evidence` | CLI logs, static and AI-enhanced reports, generated screenshot captures, run metadata and reproduction instructions. |

## Try the example

From the repository root, install the CLI and analyze the sample:

~~~bash
python -m pip install -e ".[test]"
codebase-onboard examples/toy-python-project --output toy-onboarding-report.md --static-only
~~~

The analyzer does not execute the target project. Its sample tests and CLI output are run separately by the verification workflow.

## Latest verification evidence

- [Verification walkthrough and screenshot gallery](verification/README.md)
- [AI-enhanced report with grounding-check notes](verification/toy-taskboard-ai-report.md)
- [Report from the live public GitHub download](verification/live-github-report.md)

Screenshots under `verification/screenshots/` are SVG captures rendered from saved command output and generated reports, not physical desktop recordings.
