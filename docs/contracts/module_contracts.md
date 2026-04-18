# Module IO Contracts (v1, Minimal)

This document defines **only the stable I/O contracts** needed for the current runnable workflow:

`scheme_agent` → scheme artifacts → `execution_prep` → IDE execution.

If you need broader orchestration beyond this pipeline, promote it as an experiment first (do not expand this contract).

## 1) Canonical Artifact Record (evidence)

An artifact is a repo-relative file (or directory) referenced as evidence.

Minimum required fields when you *emit an artifact record*:

- `type` (string): e.g. `scheme_artifact`, `metrics_report`
- `path` (repo-relative string)
- `fingerprint` (string): deterministic hash of **(parameters + upstream fingerprints)** whenever applicable
- `summary` (short string)

Notes:
- Prefer stable, tool-returnable envelopes (see `docs/roles/skill_contract.md`).
- Do not treat timestamps as evidence; they are metadata only.

## 2) Scheme Package Contract (current core)

The scheme phase must produce these four files under one session directory:

- `artifacts/research_plan.md`
- `artifacts/derivation.md`
- `artifacts/architecture_draft.md`
- `artifacts/experiment_design.md`

Optional (machine-readable):

- `artifacts/scheme_summary.json`
- `artifacts/experiment_matrix.json` (derived deterministically from `scheme_summary.json`)

### 2.1 Scheme Revision (human feedback loop)

Revision updates an existing scheme session in-place and produces review response evidence:

- `artifacts/response_to_review.md` (required)
- `artifacts/revision_request.json` (required; metadata + feedback fingerprint)
- `artifacts/feedback_index.json` (required; feedback items with stable ids)
- `artifacts/revision_gate.json` (required; deterministic coverage check)
- `artifacts/revision_meta.json` (required; pre/post fingerprints)

`response_to_review.md` must include one response per feedback item and include the item tag `[FB:<id>]` so coverage can be checked deterministically.

## 3) Execution Prep Contract (bridge to IDE)

`execution_prep` consumes a scheme session dir and produces an IDE-ready folder:

- copies the scheme artifacts under `.../scheme/`
- writes `NEXT_STEPS.md`
- writes a small `run_log.json` describing what was produced

### 3.1 Output layout (minimum)

Given an output root `project/execution_prep/<ts>/`:

- `project/execution_prep/<ts>/scheme/research_plan.md`
- `project/execution_prep/<ts>/scheme/derivation.md`
- `project/execution_prep/<ts>/scheme/architecture_draft.md`
- `project/execution_prep/<ts>/scheme/experiment_design.md`
- optional: `project/execution_prep/<ts>/scheme/experiment_matrix.json`
- `project/execution_prep/<ts>/NEXT_STEPS.md`
- `project/execution_prep/<ts>/run_log.json`

### 3.2 run_log.json (minimum)

- `schema_version`: `"execution_prep_v1"`
- `created_at`: UTC timestamp `YYYYMMDDTHHMMSSZ`
- `scheme_session_dir`: absolute path to the source scheme session
- `copied_files`: list of repo-relative output paths written in the workspace
- `checklist_path`: repo-relative output path to `NEXT_STEPS.md`

### 3.3 Artifact records

`execution_prep` must emit artifact records for every written output file (scheme copies + `NEXT_STEPS.md` + `run_log.json`) with deterministic `fingerprint` (content hash).

This contract does not define delivery packaging or downstream execution/backtesting modules yet; keep those as experiments until the scheme→IDE loop is stable.
