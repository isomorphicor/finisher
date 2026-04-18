# IDE execution phases (`core/ide_agent.py`)

**Goal (core experiment):** recover a simple loop — **read scheme → write `SUBTASKS.md` by module → grep-then-read rules/skills per subtask → finish one module at a time → `DONE`**. Tool **`workspace_grep`** enables **targeted** loads without embedding everything each round.

| Phase | What to do |
|-------|-------------|
| 1 | `workspace_read` on each file under `artifacts/` (paths from the first user message). |
| 2 | Write **`SUBTASKS.md`** — numbered lines aligned with **modules/phases** in `research_plan.md` / `experiment_design.md` (EDA first, then each implementation module, reporting last). |
| 2b | **Before each new `Next: #m`:** **`workspace_grep`** (regex) under `docs/` to **find** hits, then **`workspace_read`** those files — **not** full-file reads by default. System prompt is **one-shot** per run; grep keeps token use low. Optional: `docs/skills/ops/session-project-code/SKILL.md`. |
| 3 | For the **current** line only: code under **`project/src/`**, `terminal_run`, outputs under **`project/outputs/`**. |
| 4 | **`DONE`** when every line is complete or waived. |

**Defaults (`config/agents.yaml`):** `skills_inject: compact`, moderate `scheme_max_chars` — less prompt bloat, closer to early runs. Use **`INVERST_IDE_SKILLS=full`** when you want full SKILL.md bodies embedded.

See `ide_context_budget.md` for token limits and tool JSON caps.
