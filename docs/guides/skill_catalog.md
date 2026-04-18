# finisher - Skill Catalog

This document lists **Skills** (Tools) that agents can invoke.

**Current phase:** scheme-first. The repo currently focuses on producing a high-quality **scheme package** (research_plan / derivation / architecture_draft / experiment_design) via local LLMs, plus deterministic tool skills for controlled I/O and retrieval. The older spine runtime code has been removed from the repo.

Contract references:

*   Module IO and evidence artifacts: [../contracts/module_contracts.md](../contracts/module_contracts.md)
*   Validation gates: [../contracts/research_standards.md](../contracts/research_standards.md)
*   Deterministic skill contract and fingerprinting rules: [../roles/skill_contract.md](../roles/skill_contract.md)
*   Shared helpers: `core/experiment_utils.py`

## 0. Output Conventions (v1)

All Skills must:

*   accept tool arguments that match their JSON schema
*   return a structured dict-like result using the standard envelope in [../roles/skill_contract.md](../roles/skill_contract.md):
    *   `status`: `success | rejected | error`
    *   `report`: JSON-serializable structured result (no large arrays)
    *   `artifacts` (optional): evidence artifact records when files are written
    *   `errors` (optional): structured error list for `error` or `rejected`
*   fail closed on contract/quality gates via `status="rejected"` (not by returning free-form messages)

When a Skill writes files, it should also return artifact records consistent with [../contracts/module_contracts.md](../contracts/module_contracts.md) (type, path, fingerprints, inputs).

## 1. Scheme Phase Tool Skills (Active)

These Skills are used by the autonomous scheme agent (`core/scheme_agent.py`) and can also be reused by scheme-phase runners.

### `paper_search`
*   **Purpose**: Search papers (Semantic Scholar + arXiv) and return a prompt-friendly formatted block.
*   **Implementation**: `core/paper_search.py` as the retrieval backend.

### `read_file`
*   **Purpose**: Read a file under the scheme run directory (`project/` or `artifacts/`) with path safety.

### `write_file`
*   **Purpose**: Write a file under the scheme run directory with path safety (optionally restricted to an allowlist).

### `list_files`
*   **Purpose**: List files under `artifacts/` or `project/` in the scheme run directory.

## 1.1 Deterministic Post-Processing (Active)

### `experiment_matrix.json` builder
*   **Purpose**: Convert `artifacts/scheme_summary.json` into a deterministic `artifacts/experiment_matrix.json` that is easier for execution tooling to consume.
*   **Implementation**: `core/experiment_matrix.py` (`build_experiment_matrix_from_scheme_summary`).

## 2. Spine Skills (Removed)

The original v0 spine runtime skills (work items → executors → gates → delivery) are no longer shipped in this repository.

## 3. How to extend

After the scheme phase is stable, add capabilities in this order:

1. Add new deterministic Skills only when they are governance-related or universally reusable.
2. Add domain capabilities as packs or project-local code executed via `executor_execute`.
3. Keep any tool surface scoped and minimal; do not expand transport layers into “business logic”.

