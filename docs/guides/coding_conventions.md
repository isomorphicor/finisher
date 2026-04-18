# Inverst Agent - Coding Conventions

This is the minimal SOP for contributing to this repo.

## 0. Language

**Documentation and code use English.** This keeps the project accessible to the GitHub community and avoids mixed-language drift. Use English for:

- All files under `docs/` (specs, contracts, worklog, blueprints).
- Source code: comments, docstrings, log messages, and user-facing strings (CLI help, prompts that are stored in code or config).
- Config and schema text that is read by contributors (e.g. comments in YAML).

Exceptions (e.g. localized user prompts or internal notes) should be rare and documented where they occur.

## 1. Core principles

1.  **Strict Typing**: All function signatures must have type hints. Prefer built-in generics (`list[str]`, `dict[str, Any]`) and `typing.Optional`.
2.  **Configuration as Code**: Never hardcode secrets, API keys, or environment-specific paths. Use `core/config.py` (Pydantic models) which loads from `config/settings.yaml` and environment variables.
3.  **Skills are tools**: New capabilities should be implemented as deterministic skills under `skills/` and registered in `skills/registry/manifest.json`.
    *   Must be deterministic (randomness requires an explicit seed).
    *   Must return the standard envelope (see `docs/roles/skill_contract.md`).
4.  **No "Magic" Strings**: Use Enums or Constants for repeated values (e.g., model names, agent roles).
5.  **Docs as Contracts**: `docs/` defines module boundaries and IO contracts. Code should match the contracts, not contradict them.
6.  **Minimum viable code (research-first)**: Prefer the smallest correct implementation that matches the declared contract.
    *   Avoid “defensive” branches for hypothetical inputs (e.g., file type detection when the contract says “Parquet”).
    *   Add robustness only when there is a concrete failure mode or a new requirement, and record the reason.
    *   Prefer **fast paths**: vectorized `polars`, column projection, and bounded reads. Avoid accidental full-table materialization.
    *   If the task declares a concrete input contract (format/schema), **code to the contract**. Any compatibility path must cite a real failure case (in `docs/worklog.md` or a promotion decision record).

## 2. Directory Structure Rules

*   `core/`: Only for the engine, orchestration, and base classes. Do not put business logic here.
*   `skills/`: Deterministic capabilities (including governance primitives and domain logic) live here.
*   `config/`: YAML files only.
*   `data/`: Local runtime workspace (created on demand). Never commit data/artifacts; keep it ignored by git.
*   `docs/`: Contracts and decision records. Use relative links so the repo can be open sourced.
*   `<scheme_runs_root>/<project>/<session>/project/`: Project-local code for handling user requirements (default under `~/Project/projects_generated/`). Do not implement user-specific logic in repo modules.

## 3. Python Style Guide

*   Use `pydantic` for data validation.
*   Prefer `polars` for tabular IO/transforms; use `pandas` only for small data or library interoperability.
*   Avoid adding docstrings/comments unless required for a public interface or explicitly requested.
*   **Error Handling**:
    *   Prefer letting exceptions surface in internal code (`core/`) to keep logic simple.
    *   Catch exceptions at skill/CLI boundaries (`skills/`, `scripts/`) to return the standard envelope with `status="error"` and structured `errors[]`.
    *   Avoid broad `except Exception:` unless you immediately re-raise or return a structured error with enough context to debug.
*   **Dependency Policy**: Do not assume libraries exist. If a new dependency is needed, add it explicitly with a pinned version and a runnable demo/test.

## 4. Testing

*   All test code must be placed in the `tests/` directory.
*   Use `unittest` or `pytest` style assertions.
*   Do not create `demo_*.py` scripts in the root directory.
*   To run tests: `python -m unittest discover tests` or `pytest`.

## 5. Worklog & documentation

*   Keep docs minimal: update `docs/project_status.md` only when behavior/entrypoints change.
*   **Update `docs/guides/skill_catalog.md`** whenever a new Skill is implemented.
*   Prefer relative links inside markdown docs.
*   `docs/worklog.md` should only record behavior changes (no long outputs).

