# IDE execution rules (extended reference)

**Read `docs/reference/ide_core_rules.md` first.** (**§ A–D** + workflow — principle-first.) This file is an **appendix**: tiers **R/H/P**, long workflow, combinatorics, **Override** appendix, NN-vs-MLP wording. Not required for every task.

**Prompt:** `ide_execution.ide_rules_profile` **`core`** = core file only | **`extended`** = core + truncated copy of this file. Env: `INVERST_IDE_RULES_PROFILE`.

**Related (flat — pick one topic, not a reading order):** `quant_tech_stack.md` (models), `quant_soul.md` (gates).

---

## Rule tiers (summary)

| Tier | Meaning |
|------|---------|
| **R** Red-line veto | Breaks **invalidate** trading/portfolio/acceptance claims until fixed. No `DONE` on broken evidence. |
| **H** Hard | Must hold or be reconciled in `artifacts/` + `project/outputs/` (timestamps, leakage, `y` vs tradable return for PnL). **Phasing:** exploration uses time-safe train/val/test; **no CPCV combinatorics for training/HPO** until the model spec is locked — then **one** acceptance run per **`quant_soul`** (default **CPCV**; alternatives allowed if documented). **Walk-forward / forward rolling** not accepted. Blocking until aligned. |
| **P** Flexible | Acceptance protocol shape (incl. default CPCV parameters), model family, smoke budgets — change only with **written rationale** (SUBTASKS / `run_meta.json`). |

**R — Non‑negotiable (detail):** (1) **Portfolio metrics** — Sharpe / PnL / drawdown from a **defined time series** of portfolio returns (weights × **realized forward** returns per scheme/EDA). **Not** cross-sectional `y_true × f(y_pred)` as Sharpe. (2) **No lookahead** — align `quant_soul`. (3) **Honest names** — do not call output Sharpe/IC/PnL unless the computation matches. Document return column + weight rule + frequency in **`project/outputs/`** when reporting PnL-style numbers.

---

## Workflow

1. **`workspace_read`** all `artifacts/` paths from the user message.
2. **`SUBTASKS.md`** — numbered modules from scheme; order: **EDA → features/splits → baseline → eval/backtest → tuning last → report**. Top line: **`Progress: k/N complete · Next: #m · Last updated: YYYY-MM-DD`**. Lines: `[ ]` / `[~]` / `[x]` / `[!]`; **stable indices**; merge if file exists.
3. **Each new `Next: #m`:** **`workspace_grep`** on `docs/` (regex for topic), then **`workspace_read`** needed files — not full-file blind reads. Compact skills mode: SKILL bodies may be omitted from prompt.
4. **One module at a time** — code **`project/src/`**, outputs **`project/outputs/`**, stable paths (no timestamp dirs). Stuck → `[!]` with reason.
5. **Review before `[x]`** — minimal glue, vectorized. For **any** hot path — **data load/merge**, **per-day or cross-sectional transforms**, **training/backtest/nested loops** — **estimate** work (rows × passes × branches), **smoke** and **time** one unit before full scale; if full run would be multi-hour/day without user sign-off, **pivot** (subset, fewer folds, simpler transform) — do not treat “ran once” as done. Then **`[x]`** + Progress.
6. **Review gate (completion + evidence)** — Before **`DONE`** or reporting **Sharpe / CPCV acceptance / portfolio** numbers: write **`project/outputs/review_gate.md`** using **`docs/templates/ide_review_gate.md`**. Include **Session completion (review)** — **pass** or **must_fix** by checking **`artifacts/`** + **`outputs/`** + **`src/`** against the mandate (**not** inferred from **`SUBTASKS.md`** checkboxes alone; those can be wrong). Then evidence tables (R-line: tradable return vs label, leakage, honest names). **Tier R** — no `DONE` on broken R-line evidence until fixed or waived **`[!]`** + rationale in **`SUBTASKS.md`**.
7. **`DONE`** only when step 6’s **completion** verdict allows it **and** every numbered SUBTASKS item is **`[x]`** or waived **`[!]`** (portfolio-style sessions must also satisfy evidence rows in **`review_gate.md`**).

**Tools:** read before overwrite; `terminal_run` uses **`cwd`** (repo-relative), not `cd` alone. Baseline smoke budgets: **`quant_tech_stack`**. `PROJECT_ROOT = Path(__file__).resolve().parent.parent` → **`project/`**.

**Layout:** library under **`project/src/`**; artifacts under **`project/outputs/`** (or `INVERST_IDE_OUTPUTS_SUBDIR`). External data via **env** + comments, not only absolute paths.

## Review gate (artifact)

Normative for sessions that output **Sharpe / PnL / CPCV acceptance / portfolio** claims, and for **session completion**: **`review_gate.md`** carries a **Session completion (review)** verdict — analogous in role to **`review_scheme_package`** after the scheme phase (human or model reviews substance, not checkbox state alone). Template: **`docs/templates/ide_review_gate.md`** → **`project/outputs/review_gate.md`**. A **separate** reviewer-only pass (read `src/` + `outputs/`, no writes to `src/`) may fill the same file; the execution agent still **must** produce it when it ships those claims unless the mandate explicitly excludes portfolio metrics.

**EDA:** probe columns/rows/ranges → short **`outputs/`** snapshot → then explicit loader (**not** huge `infer_*` without real column names).

**Panel:** avoid default **`bfill`** as lookahead; prefer **`fillna(0)`** / indicators unless scheme says otherwise. Vectorize; no fat Python loops over full matrices.

**Pipeline & I/O (same tier as training cost):** Wall time is **not** “CatBoost minutes” alone. **Heavy** panel paths: **`ide_core_rules.md` § B** — **Polars-first** at scale; pandas for small/glue; no full-panel naive loops. If preprocessing would eat the session budget, **pivot** — same discipline as **Combinatorics & training cost** below.

**Rules under load:** No session can obey every linked doc verbatim. **Minimum stack:** **`ide_core_rules.md`** + **Workflow (numbered steps)** + **`SUBTASKS.md`** + any user **`## Override`** block. Tier **R** / **`quant_soul`** acceptance beats peripheral checklists. Pull **`quant_tech_stack`**, **`quant_soul`**, and skills **on demand** via **`workspace_read`** — do not treat long rule lists as a sequential mandatory checklist.

**Style:** small mechanical steps (~10–25 lines real logic); refactor glue-only files **>~80–100 lines** without real math.

**Modeling order:** features + splits + **baseline** → eval → then HPO/`optimize` — not the reverse. **Tabular:** trees (CatBoost) are the expected workhorse — **features first**; see **`quant_tech_stack`** → **Tabular prior** & **GBDT: fixed iterations**. On **daily** data with features ready, CatBoost (incl. typical acceptance CPCV) is usually **cheap wall-clock** — a sensible **default first model**, not a placeholder. **Ensembles** may beat a single tree; a **non-tree** model weaker than baseline **alone** may **stay** if **ensemble with trees** **≥** baseline (`ide_core_rules.md` **§ C**).

**Acceptance phasing (mandatory):** Exploration = time-safe **train/val/test** only; **no CPCV combinatorics** for train/HPO. **Acceptance** after lock = **`quant_soul` §3** — default **one** CPCV-style run; **other time-safe** designs allowed if **named and justified**; **not** walk-forward / forward rolling. **Multi-*y*:** **`ide_core_rules.md` § C** — run **cheap CatBoost baseline** (group/weights + one fit) **before** heavy acceptance or per-label work; document in `SUBTASKS` / `run_meta.json`. **Splits / phasing:** **§ D**.

**Scheme vs repo defaults (IDE may revise):** If `artifacts/experiment_design.md` (or related scheme files) **omit** repo defaults (e.g. **CatBoost** as primary GBDT baseline, cheap multi-*y* CatBoost before per-label) or **predate** current rules, **edit the artifacts** to align and add **`project/outputs/plan_delta.md`** (or a short section in `run_meta.json`): **what changed** and **why**. This is **alignment**, not a waiver of **R** / `quant_soul`. Scheme phase should catch most gaps via **`tabular_baseline_gate.json`**; IDE fixes what slipped through.

---

## Combinatorics & training cost (mandatory)

**Scope:** This section is **training / CV / HPO enumeration**. **Pipeline & I/O** overhead (above) applies **before** the first `fit`.

**Acceptance job counts** (e.g. CPCV splits when CPCV is the chosen protocol) apply to the **acceptance** run (locked model), not to exploration — do not multiply acceptance splits by HPO grids during model selection.

Before **combinations / grids / nested CV**: write **what** is enumerated and **how many** jobs (e.g. **C(N,k)** for k test blocks of N — each full retrain = one job unless shared weights). **Default combinatorial CPCV when k>1:** **N=6, k=4** → **15** splits; document changes. If **>~20–25** full training jobs for a milestone, justify in SUBTASKS or **`run_meta.json`**.

**Time budget:** Estimate jobs + rough time before loops (`run_meta.json` / `training_plan.txt`). **Stop** wrong-scale runs; smoke first; **Pivot:** note in SUBTASKS + shrink splits/data/order of work. A design where **one training round** routinely takes **hours or days** (unless explicitly approved) is **not** compatible with iterative research — shrink until a round is on the order of **minutes to low tens of minutes** for exploration, or document why not.

**Multi-model (session skip list):** Same smoke, same slice — log times in **`outputs/`**. Throughput is **hardware- and data-dependent**; do not copy others’ seconds. **Illustrative only (not a SLA):** ~10M rows, one setup saw **GBDT ~10–30 s/fold (CPU)** and **NN <~2 min/epoch (GPU)** — your machine may differ **orders of magnitude**. Record in **`run_meta.json`**: **`n_rows`**, **device** (`cpu`/`cuda`/`mps`), **unit timed** (fold/epoch). **Same machine, same smoke:** skip rest of session if **>~10×** slower than next peer **or** one comparable unit **>~10 min** with sane hyperparameters → **`skipped_models_this_session.json`** (`slow_vs_peers` / `slow_wall_clock`). No permanent repo ban unless user requires.

---

## Override (`## Override` in `--task`)

Not a waiver of **R / quant_soul**. **`workspace_read`** artifacts vs code; fix gaps. **Appendix below** is **mandatory order**; step **(0)** `scheme_alignment_audit.md` is **blocking**.

**Long runs:** Anchor on **SUBTASKS** (`Next: #m`); **targeted** `artifacts/` for current module only — not full reread every round. Column/return definitions from **scheme + EDA**, not memory.

---

## Related reference (do not duplicate)

| Topic | Doc |
|-------|-----|
| GBDT/NN/pretrain, exploration | `docs/reference/quant_tech_stack.md` |
| Phases, rounds | `docs/guides/ide_execution_phases.md` |
| Context budget | `docs/guides/ide_context_budget.md` |
| Report template | `docs/templates/execution_report_ide.md` |
| Hard gates + tiers | `docs/policies/quant_soul.md` |
| Paths / MPS / CatBoost | `docs/skills/ops/session-project-code/SKILL.md` |
| Data-first probe | `docs/skills/ops/data-first-execution/SKILL.md` |

---

## Maintenance

Edit **this file** to change IDE behavior. Skills **link** here.

---

<!-- BEGIN:OVERRIDE_FOLLOW_THROUGH -->
**Override follow-through (mandatory — execute in order):** (0) **First deliverable:** `workspace_write` **`project/outputs/scheme_alignment_audit.md`**. Use a **table**: `project/src/` module | `artifacts/` refs (file + subsection) | aligned? Y/N | gap in one line | planned fix (or "none"). Cover every module that implements scheme stages; use `workspace_list` / `workspace_read` on `project/src/` if needed. If the user only asked a tiny scope tweak, still add one row or a short "scope-only override" note — **do not skip this file.** (1) Map Override to modules (if unclear: split, label/target, train, backtest, metrics). (2) For each gap with N, **`workspace_read`** artifacts + code; fix **math + columns + splits**. (3) **Change** code — including **`[x]`** lines if wrong. (4) **`terminal_run`**; refresh **`project/outputs/`**; update **SUBTASKS** if you reopened a module. Do **not** treat "already runs" as "already correct"; do **not** skip (0).
<!-- END:OVERRIDE_FOLLOW_THROUGH -->
