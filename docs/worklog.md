# Worklog (Minimal)

This file is a lightweight, human-readable log of **key behavior changes** and **decisions**.

Rules:
- Only record changes that affect how to run the project, artifact contracts, or gates.
- Prefer short entries. Do not paste long prompts or outputs.
- If nothing important changed, do not write an entry.
- Keep entries in reverse chronological order (newest date first).

---

## 2026-04-12

- **IDE exploration anti-loop:** In `exploration_mode`, `terminal_run` no longer avoids stall forever: consecutive rounds with `terminal_run` but no `workspace_write` increment a streak; at **8** (warn) and every **3** rounds after, inject a nudge; at **16** (exit) return `stalled` (`INVERST_IDE_EXPLORATION_TERMINAL_STREAK_WARN` / `_EXIT`). Mitigates endless similar pandas probes during EDA.
- **`run_research_session` Phase 0:** Positional scheme **task** (data paths, constraints) is **prepended** to exploration IDE so probes use real paths — not only `<session>/project/`. Default `DEFAULT_IDE_EXPLORE_TASK` states data may live outside `project/`.
- **Scheme after EDA:** If Phase 0 exits `success`, the scheme agent receives `SCHEME_TASK_AFTER_EDA_PREFIX` — must `read_file` `project/outputs/eda_report.md` before drafting artifacts (not automatic file injection; tool-based read).
- **`run_research_session` EDA → scheme → IDE:** `--explore-task` applies **only** to Phase 0 exploration; `--ide-task` applies **only** to the final IDE phase (no longer mixed). Alias `--eda-first` for `--explore-before-scheme`. Default explore string mentions return/PnL-related columns when present. `--full-experiment-report` appends a hint (return/risk vs baseline, costs, limitations, review gate) to the final IDE task.
- **Chunked supervisor (standalone):** `scripts/run_supervisor_ide.py` + `core/supervisor_ide_loop.py` — text-only **CIO** JSON (`continue`, `next_focus`) reads capped `SUBTASKS` / review gate / `WORKLOG`, then **chunked** `run_ide_execution_agent`; uses `LLMService` (same provider as IDE: Ollama for cheap runs, API via `settings.llm.provider`). CIO model: `resolve_supervisor_cio_model` in `core/ide_execution_config.py` (`--cio-model` > `INVERST_CIO_MODEL` > `agents.yaml` `supervisor.cio_model` > `agents.cio.model` > `settings.llm.default_model`). Outputs: `project/outputs/cio_directive_latest.json`, `supervisor_run.jsonl`, `supervisor_summary.json`. Not wired into `research_session_pipeline`. Contract allowlist: `run_supervisor_ide.py`.
- **Phase 3 (docs):** `docs/skills/ARCHITECTURE.md` splits supervisor roadmap into **3a** (linear CLI + explore flags, in repo), **3b** (manual supervisor checklist), **3c** (automated supervisor — still future). New ops skill [`docs/skills/ops/manual-supervisor-playbook/SKILL.md`](skills/ops/manual-supervisor-playbook/SKILL.md); [`research-orchestration`](skills/ops/research-orchestration/SKILL.md) v1.1.0 adds runtime flag table; [`cognitive-research-flow`](skills/ops/cognitive-research-flow/SKILL.md) links to 3b; `manifest.json` registers `ops.manual-supervisor-playbook`.
- **Task runners:** `core/task_runners.py` `ide_execution_agent` mode accepts optional **`iteration_mode`** / **`exploration_mode`** (tri-state: omit → env defaults; `true`/`false` / `1`/`0`).
- **IDE exploration mode:** `core/ide_agent.run_ide_execution_agent(..., exploration_mode=...)` skips the “four scheme artifacts required” gate when enabled; user prompt uses exploration mission + optional scheme placeholders (`INVERST_IDE_EXPLORATION` / `--explore-only` on `scripts/run_ide_execution_agent.py`). `run_meta.json` records `exploration_mode`.
- **Pipeline:** `core/research_session_pipeline.py` adds `--explore-before-scheme` — ensures `<runs_root>/<project>/<session>/`, runs exploration IDE, then scheme → prep → IDE; default EDA string when `--ide-task` is empty for that phase only (`DEFAULT_IDE_EXPLORE_TASK`).
- **Session helper:** `core/scheme_paths.ensure_scheme_session_dir` (already present) used by the explore-before-scheme path.
- **Smoke experiment:** `docs/experiments/smoke_plan_and_code.md` + `scripts/smoke_research_session.sh` + `scripts/smoke_research_session_task.txt` — validates scheme artifacts + IDE file in one session.
- **Smoke iteration:** First run failed (`E_SESSION_PATH`) when `INVERST_SCHEME_PHASE_RUNS` was under `/tmp` while `--workspace-root` was the repo — prep requires session inside workspace. Script now defaults `INVERST_SCHEME_PHASE_RUNS` to `<repo>/out` and picks Python 3.10+ (conda/local). Second run exited 0; `out/smoke_plan_code/main/project/src/smoke_hello.py` created.
- **Skill-first entry:** added `scripts/run_research_session.py` and `core/research_session_pipeline.py` (shared scheme → prep → IDE pipeline). `scripts/run_scheme_then_ide.py` now calls the same pipeline.
- **Deprecated** `scripts/run_autonomy_loop.py` (stderr warning + module docstring); README points to `run_research_session.py` / `run_scheme_then_ide.py`.
- **Docs:** `docs/skills/ARCHITECTURE.md` (L0–L3, L2 runtime mapping).

## 2026-03-25

- Tightened `docs/agent/` contracts; clarified CIO-only interface + dynamic hiring; added no-topic autonomy (`artifacts/ideated_task.json`).
- Slimmed quant policy and contracts: `docs/policies/quant_soul.md` is enforceable-only; `docs/contracts/*` aligned to scheme→execution_prep workflow.
- Reduced docs drift: simplified `docs/README.md` entrypoints and removed references to unimplemented scheme parallelism.
- Removed non-core helper scripts (`scripts/benchmark_ollama_mlx.py`, `scripts/download_models.py`) to keep the repo minimal.
- Removed unused legacy module `core/experiment.py` (unreferenced; pandas-only dependency).
- Removed unused legacy modules `core/workspace.py`, `core/experiment_logger.py`, and `core/souls.py`.
- Slimmed core runtime code without capability regressions:
  - simplified `core/config.py` to current runtime fields only,
  - removed redundant parsing/persistence in `core/scheme_agent.py`,
  - simplified `core/llm.py` fallback flow,
  - removed dead helpers from `core/experiment_matrix.py`, `core/quant_gate.py`, and reduced `core/experiment_utils.py` to the minimal active surface.

## 2026-03-22

- Scheme phase stabilized as the only runnable focus (design-only).
- Added autonomous scheme agent with refine + structure/keyword/topic gates.
- Added optional runtime artifacts (generated per run when enabled): `artifacts/scheme_summary.json` and deterministic `artifacts/experiment_matrix.json`.
- Removed legacy “LLM writes code + sandbox execute” runtime and its scripts.
- Slimmed docs to a minimal set aligned with the current runnable path.
