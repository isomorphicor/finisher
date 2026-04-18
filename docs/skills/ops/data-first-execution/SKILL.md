---
name: data-first-execution
type: ops
version: 2.2.0
triggers:
  - data exploration
  - EDA
  - ide execution
  - preprocessing
  - session project
  - subtask
  - decomposition
  - checklist
applies_to:
  - ide_execution_agent
  - repo
links:
  - docs/reference/ide_core_rules.md
  - docs/reference/ide_execution_rules.md
  - docs/guides/ide_execution_phases.md
  - docs/guides/ide_context_budget.md
  - docs/experiments/scheme_phase/workflow.md
  - docs/experiments/scheme_phase/local_data_stocks.md
---

## Data-first execution (session `project/`)

**Rule:** Implement from **real data**, not a generic full pipeline. Round targets: **`docs/guides/ide_execution_phases.md`** — ship a small `eda_report.md` early.

**Minimal rules** are in **`docs/reference/ide_core_rules.md`** (embedded in the IDE system prompt by default). **Extended** tiers/workflow: **`docs/reference/ide_execution_rules.md`** (`ide_execution.ide_rules_profile`). **Do not duplicate** full content here.

### Mandatory workflow (summary)

1. **Probe** — `terminal_run`: real columns/dtypes/nrows → save under **`project/outputs/`**.
2. **Load / preprocess / split** — short scripts after probe; vectorized ops. **Cost:** preprocessing can dominate wall time — see **`docs/reference/ide_execution_rules.md`** (**Pipeline & I/O**); estimate and smoke **before** full panel passes, not only before `fit`.
3. **Model / eval** — after 1–2; training budgets: **`docs/reference/quant_tech_stack.md`**.

**Tool discipline:** after EDA exists, the next step must be **`terminal_run` or `workspace_write`** — not prose-only turns.

### Anti-patterns

- Fortress loaders, speculative column inference, or pipelines **before** one successful read + column list.
- **Fat glue:** multi-hundred-line scripts for load/merge/fill/split when EDA already fixed the schema — collapse to short **Polars** (large) or **pandas** (small) per **`ide_core_rules.md` § B**.
- Architecture dumps **before** file → aligned frame works.
- Same session: thin scripts first; **restart** `run_ide_execution_agent` if you hit `max_rounds` — `project/` persists.
- **Hot-path preprocessing:** nested Python loops over **dates × columns** (or **groupby** + **concat** per day) on the full panel for transforms that could be **`groupby(...).transform`** or one vectorized pass.

### Checklist

- [ ] SUBTASKS + Progress before big integration.
- [ ] EDA artifact before large `src/` package.
- [ ] Load/merge uses **observed** keys/columns.
- [ ] `execution_report.md` uses **`docs/templates/execution_report_ide.md`** (incl. baseline training contract).

**See also:** **`docs/skills/ops/cognitive-research-flow/SKILL.md`** — probe vs scale, cost–benefit per step, and HPC discipline (complements this workflow skill).
