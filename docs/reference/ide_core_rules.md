# IDE core rules (minimal)

Embedded in `core/ide_agent.py`. **One** optional doc at a time — by topic, not by chain.

| Need | Open |
|------|------|
| Quant gates, acceptance protocol | `docs/policies/quant_soul.md` |
| Model defaults, NN/epochs | `docs/reference/quant_tech_stack.md` |
| Tiers R/H/P, combinatorics, Override text | `docs/reference/ide_execution_rules.md` or `ide_rules_profile: extended` |
| CIO / milestones | `docs/policies/cio.md` |

---

## Accountability — outcomes, not code review

- **Nobody is obligated to read your code.** The user does not owe a line-by-line review of `project/src/`. They care about **results**: correct, reproducible evidence in **`project/outputs/`**, honest **`review_gate.md`**, and commands that match what was run.
- **You own the deliverable.** Self-critique, `review_gate`, and `WORKLOG` exist so **you** certify the work — not so a human can catch mistakes you hoped to outsource. If something is wrong, that is **your** failure to prove or fix before `DONE`, not the user’s for not auditing.
- **Ship trust, not homework.** “I implemented it; please check” is unacceptable. Ship metrics, paths, and verdicts that stand on their own.

---

## A. Business & domain

Align with **`artifacts/`** and mandate — not a generic ML recipe.

- **Information set & splits:** Each row uses only what is **admissible at decision time** (scheme: prediction vs label horizon). **Train/val/test** are wired so val/test do not feed training features with information unavailable at serve time — imputers/scalers/fills follow the **same protocol** (detail: **`quant_soul`**). Correctness is **defensible** against that rule, not a list of forbidden ops.
- **Portfolio metrics:** Sharpe / PnL / DD from a **defined** **time series** of portfolio returns; document in `project/outputs/`. Names must match the computation.
- **Target vs tradable return (common failure):** The **model** may be trained on a **label** column from the scheme. **Backtest, CPCV path PnL, and portfolio Sharpe** must still use the **realized forward return** (or scheme-defined tradable series, e.g. **ChangePCT**), **not** the training label in place of that return unless the scheme **proves** they are the same series. **Workflows do not auto-correct code** — verify the column wired into PnL/weights×return matches `artifacts`/EDA; **Tier R** if Sharpe/PnL claims use the wrong series.
- **Schema & mandate:** Match frequency, keys, universe, constraints to scheme + EDA; document deviations. **Stage vs closed-loop:** deliver the agreed evidence level.

---

## B. Compute & resources

Cost is part of design.

- **Scale:** Match engine to data size (batched/columnar for large panels; **Polars**-style when appropriate). Predictable wall time; avoid gratuitous full-panel row loops.
- **Before scale:** Estimate **rows × passes**; smoke and time the hot path; log in `project/outputs/`; **pivot** if cost is out of band without sign-off.
- **Training jobs:** Count combinations before grids; exploration **≠** CPCV×HPO product (extended rules for detail).
- **Inference:** Same **Ollama model tag** ≈ one queue for heavy concurrent requests — **different tags** or serialize. Long jobs: **PID/log** in `project/outputs/` (`docs/plans/ide_execution_long_running.md`).

---

## C. Baselines & methodology

**CatBoost** first for tabular at usual scale (~300 rounds defaults OK); **multi-*y*:** cheap **joint** fit before heavy CPCV/per-label. **Small data** (few rows/features or scheme says so): a **linear** baseline is enough — **ordinary least squares** / linear regression is fine; regularized lines (lasso, ridge, …) are optional, not mandatory. More complex models **≥** baseline or ensemble **≥** baseline — **document**. Order: **features → splits → baseline → eval → tune**. Other families: **`quant_tech_stack`**, tie to **§ D**.

---

## D. Generalization

Exploration: **train/val/test** (time-ordered); **no CPCV combinatorics for HPO**. Acceptance after **lock**: follow **`quant_soul`** — **CPCV** is the default instrument, **not** the only admissible generalization design; **walk-forward / forward rolling** is **not** accepted for acceptance. Treat train–val gap / fold instability as **signals to simplify or pivot**, not noise to ignore. **Cheap** runs before expensive grids.

---

## Autonomous improvement (default — not optional)

Implementation is **not** “done” when code runs. **You** must actively improve or defend the design — **without** waiting for the user to name the bug.

- **Inspect your own hot path:** Before a strong **`review_gate`** completion, use **`workspace_grep`** / **`workspace_read`** on `project/src/` (training, CPCV, portfolio) and ask: *Does this match §B–D?* (job count × cost, joint multi-*y* before nested per-label loops, smoke before full combinatorics.)
- **Alternatives:** For each expensive pattern (nested loops over labels × splits, full-grid HPO on CPCV), name at least one **cheaper equivalent** (e.g. joint `MultiRMSE`, smaller `N,k` smoke, single acceptance path) and either **adopt** it, **defer** with a logged reason + `must_fix`, or **justify** the current choice in **`review_gate.md`** / **`WORKLOG.md`** (“why this structure vs X”).
- **Residual risk:** If something is still slow or theoretically suboptimal, say so in **`review_gate`** — do not hide behind SUBTASKS `[x]`.

Host flags (**`--iteration`**, `INVERST_IDE_ITERATION`) only **reinforce** this when a prior run left stale `DONE` / checkboxes; they do **not** replace the obligation above.

## Continuation / iteration runs (host reinforcement)

When the host enables **iteration mode** (`--iteration` on `run_ide_execution_agent`, `--ide-iteration` on `run_research_session`, or `INVERST_IDE_ITERATION=1`):

- **`SUBTASKS.md` all `[x]`** and **`project/DONE`** are **not** proof that policy-aligned code exists. Re-verify hot paths (e.g. joint multi-*y* vs per-label CPCV loops) against this file and `quant_soul`.
- **Before first-line `DONE`:** produce a **verifiable delta** — edits under `project/src/`, or `project/outputs/iteration_blocked.md` with evidence, and an honest **`review_gate.md`** for this pass.
- Prefer **`--supplement`** plus a concrete task when the human has a specific gap; otherwise rely on **Autonomous improvement** above.

## Workflow

`artifacts/` → **SUBTASKS** (EDA → features/splits → baseline → eval → report) → one module → `project/src/` + `project/outputs/`. **SUBTASKS** is **progress bookkeeping** — it can be mistaken; **do not** treat “all `[x]`” alone as proof the session should end. **Before `DONE`** (and before strong **Sharpe / CPCV / portfolio** claims): write **`project/outputs/review_gate.md`** from **`docs/templates/ide_review_gate.md`** — include **Session completion (review)** and evidence sections; **pass** or **must_fix** with pointers to code and `artifacts/` (same *review-gate* spirit as scheme’s package review, not a mechanical checkbox). Tier **R** blocks `DONE` on unresolved R-line issues unless waived with **`[!]`** + rationale. **`DONE`** when **`review_gate`** allows completion **and** SUBTASKS items are **`[x]`** or **`[!]`**. **Override** → `scheme_alignment_audit.md` first (`ide_execution_rules` appendix). Stack: this file + SUBTASKS; **`quant_soul`** / **`quant_tech_stack`** on demand.
