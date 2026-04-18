# finisher - Project Status

**Active Memory for the AI Development Team.**
This file tracks the current state, recent accomplishments, and immediate next steps.

## 1. High-Level Summary

*   **Project Name**: finisher
*   **Version**: 0.3.0 (Alpha)
*   **Goal**: Build a research-first quant stack where the LLM plans/synthesizes and deterministic Skills produce evidence artifacts.
*   **Current State**: **Scheme design only** + IDE for code/experiments. Primary entrypoint: `scripts/run_scheme_agent.py` (autonomous scheme agent) backed by `core/scheme_agent.py` and deterministic scheme-phase tool skills (`skills/scheme_phase.py`). Legacy non-autonomous runners have been removed to avoid drift.

## 2. Recent Accomplishments

*   ✅ **Scheme phase (runnable):** `scripts/run_scheme_agent.py` — autonomous, skill-driven scheme agent writing the scheme package under `out/<project>/<session>/artifacts/` (default project: `default`). See [experiments/scheme_phase/blueprint.md](experiments/scheme_phase/blueprint.md).
*   ✅ **Scheme workflow:** [experiments/scheme_phase/](experiments/scheme_phase/) — scheme-phase workflow docs aligned to the runnable agent.
*   ✅ **Contracts**: Kept contracts minimal and aligned to the runnable workflow in `docs/contracts/`.
*   ✅ **Standards**: Updated validation protocols to be evidence-driven and time-safe in `docs/contracts/research_standards.md`.
*   ✅ **Docs hygiene**: Converted doc links under `docs/` to relative paths for open sourcing.
*   ✅ **Scheme phase (current)**: `scripts/run_scheme_agent.py` is the single entrypoint. Shared helpers were reduced to the minimal runtime surface.
*   ✅ **Task entry**: `main.py` and `run_research_task(task)` in `core/task_runners.py`; modes `design_only`, `scheme_agent`, `execution_prep`.
*   ✅ **Autonomy hardening (scheme_agent):** Added `refine_user_need_to_task` (`artifacts/refined_task.json`) plus deterministic structure/keyword gates (`artifacts/structure_gate.json`, `artifacts/topic_anchor_gate.json`) and LLM topic alignment (`artifacts/topic_alignment.json`). Optional `artifacts/scheme_summary.json` and derived `artifacts/experiment_matrix.json` via CLI.
*   ✅ **No-topic autonomy**: if the user provides an empty task, CIO ideates a bounded quant topic and records `artifacts/ideated_task.json`.
*   ✅ **Codebase slimming**: Removed unreferenced legacy modules and simplified `core/config.py`, `core/llm.py`, `core/experiment_utils.py`, and `core/scheme_agent.py` while keeping runnable behavior unchanged.

## 3. Active Roadmap

**Current execution path:** scheme phase only (design artifacts + gates). The execution phase is intentionally done in the IDE.

### Phase 0: Contracts → Scheme Phase (Completed)
*   [x] **Scheme phase stabilized**: scheme agent + deterministic gates + structured outputs.

### Phase 1: Hardening (Next)
*   [ ] **Human review → revision**: implement revision entry and response artifacts.
*   [ ] **Regression**: add deterministic spine tests for the runnable scheme path.

### Phase 2: IDE Integration (Next)
*   [ ] **Execution prep contract**: define "scheme package → IDE-ready workspace" outputs.
*   [ ] **Machine-readable design**: optionally emit structured experiment design for tooling.

### Phase 3: Trading & Execution (Planned)
*   [ ] **Execution interface**: standard interface (Signals -> Weights) to wrap external engines.
*   [ ] **Mock backtester**: minimal placeholder for demos.
*   [ ] **Risk manager**: hard-coded risk constraints (Line 2 Defense).
*   [ ] **HJB solver**: optional optimal control component when needed.

## 4. Known Issues / Tech Debt

*   **Avoid architecture drift**: implementation must follow the contracts; do not reintroduce ad-hoc loops.
*   **Tool surface control**: When Phase 2 adds IDE/MCP, scope file/terminal access to run workspace; default no-network.
*   **Testing**: spine tests are archived; add deterministic tests for scheme phase and `core/experiment_utils` once flow is stable.

## 5. Next Session Goal

*   **Priority:** Keep scheme phase stable; use `execution_prep` as the bridge from scheme artifacts → IDE-ready checklist/workspace.
*   Optional: open-source release boundary (e.g. exclude `AI_Investment_Team_Plan.md`) once the path is stable.

## 6. Next-Phase Development Suggestions

Recommendations for the next stage, in priority order.

### 6.1 Phase 1: Hardening

*   **Human review → revision entry**: Implemented `--revision --run-dir <path> --feedback <file>` to revise a session in-place and write `artifacts/response_to_review.md` plus deterministic revision artifacts.
*   **Observability and regression**: Add simple output checks for scheme runs (required sections/anchors) and a short session summary artifact for comparisons.

### 6.2 Phase 2: IDE integration

*   **Tooling and contract**: Define the "scheme package → IDE executable" contract: given `out/<project>/<session>/artifacts/`, which dirs/files to create or update in the target workspace and what the default entry command is.
*   **Minimal viable integration**: Do not aim for full automation. Goal: agent or script copies/links the **current session's scheme package** (research_plan, architecture_draft, experiment_design) into a workspace and produces a "suggested next steps" list (e.g. create src/, scaffold modules per architecture_draft, run Exp1 from experiment_design); human executes in the IDE.
*   **MCP/API scope**: If using MCP, limit to "read/write workspace files + trigger run"; execution and debugging stay inside the IDE; do not rebuild a sandbox.

### 6.3 Phase 3: Trading & execution preparation

*   **Executable experiment matrix**: If "execution order" and "pass conditions" in experiment_design are structured (YAML/JSON), add a **read-only** parser or small script: input `experiment_design.yaml`, output "pending experiments list" or "next-step suggestions"; do not auto-run yet, only provide a clear checklist for human or IDE.
*   **Result backfill**: For a future "run complete → update design doc" flow, define result file format under `experiments/results/` or artifacts and align with experiment_design metrics/pass conditions.

### 6.4 Engineering and governance

*   **Testing**: Keep deterministic tests focused on current runtime helpers (`missing_artifacts_in_dir`, read/write under run root, scheme gates) and avoid reviving archived helper surfaces.
*   **Doc–code sync**: When changing run commands or args, update [experiments/scheme_phase/blueprint.md](experiments/scheme_phase/blueprint.md) and worklog so the blueprint does not drift from the script.
*   **Known issues**: Phase 0 "MCP / Sandbox" can be marked "deferred until Phase 2 IDE choice"; Testing as "add scheme-phase and experiment_utils tests when stable".
