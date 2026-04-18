---
name: scheme-phase
type: ops
version: 1.3.0
triggers:
  - scheme phase
  - scheme
  - blueprint
  - experiment design
applies_to:
  - repo
links:
  - docs/experiments/scheme_phase/blueprint.md
  - docs/experiments/scheme_phase/workflow.md
  - docs/reference/ide_execution_rules.md
---

## Ops Skill: Scheme Phase (Playbook)

### Purpose

Run the **scheme phase experiment** consistently, produce auditable artifacts under `out/`, and keep the workflow aligned with the blueprint.

**Not always first:** Scheme design is **one** capability in the stack. For unknown data or mandate, [`docs/skills/ops/research-orchestration/SKILL.md`](../research-orchestration/SKILL.md) may recommend **EDA / exploration** (e.g. IDE `--explore-only`) **before** locking the four artifacts. The linear `run_research_session.py` pipeline can run **`--explore-before-scheme`** to match that order.

**End-to-end compute:** Scheme packages must not implicitly treat **training** as the only expensive stage. For tabular/panel work, call out **data I/O + feature pipeline** (vectorized vs loop-heavy) when non-trivial — IDE enforces **pipeline & I/O cost** alongside model budgets (**`docs/reference/ide_execution_rules.md`**).

### Preconditions

- You have a runnable Python environment for this repo.
- You have a local model endpoint configured (or an API backend) compatible with the configured scripts.

### Steps

1. **Pick a request** (fuzzy idea → scheme package).
2. **Run the autonomous agent** (skill-driven file writing):
   - `python scripts/run_scheme_agent.py --model <MODEL> --lang en "<request>"`
3. **Collect evidence**
   - Confirm `<runs_root>/<project>/<session_or_ts>/artifacts/` (repo default: `out/<project>/<session>/...`) contains required artifacts.
4. **If local-data stocks experiment**
   - Use `docs/experiments/scheme_phase/local_data_stocks.md` as the canonical recipe.

### Verification

- Required artifacts exist:
  - `research_plan.md`, `derivation.md`, `architecture_draft.md`, `experiment_design.md`
- **Quant / tabular:** `experiment_design.md` must name **CatBoost** as the **primary** GBDT baseline (see `docs/reference/quant_tech_stack.md`). Listing only LightGBM/XGBoost without CatBoost fails the **`tabular_baseline_gate`** (`artifacts/tabular_baseline_gate.json`) until revised.
- **Pipeline cost (when relevant):** If the design includes **wide panels**, **per-date cross-sectional steps**, or **multi-table merges**, `experiment_design.md` or `architecture_draft.md` should state that implementation follows **vectorized / single-pass** patterns (or justify an unavoidably heavier path). Silently assuming “only the model matters” is misaligned with **`ide_execution_rules`** (pipeline & I/O).
- **Success criteria / pass conditions** must not use arbitrary blog-style numbers (e.g. fixed Sharpe or turnover %) unless they come from the user mandate or a cited calibration; otherwise keep targets `provisional` / TBD with a clear calibration path (`docs/policies/quant_soul.md`).
- If quant-related, the quant gate must pass (see `docs/policies/quant_soul.md`).
- Protocol staging is explicit:
  - exploration protocol vs acceptance protocol (CPCV path-based) are separated in the scheme package.
  - planning parameters for CPCV/time-splits are marked `provisional` and become `locked` only after data exploration.

### Rollback

- No rollback needed; outputs are written under `out/` (ephemeral). Delete the session directory if needed.

