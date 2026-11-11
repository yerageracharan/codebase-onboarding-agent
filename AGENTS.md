# Agent Instructions

These instructions apply across Codebase Onboarding Agent.

## Product invariants

- Repository analysis is static and evidence-forward. Never execute code, scripts, package hooks, build steps, or install commands from the target repository.
- Do not expose or copy secrets from scanned repositories. Preserve secret-file exclusions and value redaction.
- Distinguish manifest facts, AST-derived symbols, filename heuristics, and model-generated suggestions in both code and reports.
- Treat downloaded repository archives as untrusted input; preserve path traversal checks and archive-size/member limits.
- AI validation may remove unsupported claims, but deterministic inventory remains authoritative for file paths, manifests, and line locations.

## Repository map

- `src/codebase_onboarding_agent/`: repository access, inventory, analysis, validation, entry-point detection, report generation, and CLI.
- `tests/`: synthetic repository fixtures and regression tests.
- `examples/` and `docs/`: safe usage examples and user documentation.
- `SKILL.md`: optional assistant integration guidance, not the Python CLI itself.

## Implementation rules

- Read the relevant source, callers, tests, and documentation before changing a boundary.
- Keep file inventory deterministic and bounded.
- Do not relax ZIP traversal, symlink, member-count, compressed-size, expanded-size, or secret-redaction protections to make a test pass.
- Any new parser must operate on data as data; never import or execute scanned modules.
- Never include secret values in diagnostics, generated screenshots, fixtures, or reports.
- Do not claim static analysis proves runtime behavior.

## Validation

```bash
python -m pytest -q
codebase-onboard --help
python -m compileall -q src tests
```

## Change ownership and proof

- Keep one authoritative owner for each domain rule and each persisted state. UI, CLI, MCP, and provider adapters translate inputs and outputs; they must not reimplement business policy or become competing sources of truth.
- Before changing a contract, trace the input through its owner to every consumer. Update callers, schemas, examples, docs, and regression tests together. Remove superseded paths unless a documented public-compatibility requirement keeps them.
- Keep optional external model/provider integrations behind adapters. Use injected or mocked adapters for deterministic unit tests; label live network/provider checks separately and never describe a mock as live verification.
- Validate untrusted user, model, file, and network data at the boundary. Preserve the product's evidence/provenance rules and reject malformed inputs rather than silently inventing defaults.
- Verify the supported user entry point and at least one relevant failure path. Report exact commands and results; CI on a different commit SHA is not proof for the current change.
- Keep the root README as the user entry point, `docs/README.md` as the documentation map, and focused guides as the owners of detailed contracts. Update links when files move. Do not hand-edit generated output when a source or generator owns it.
