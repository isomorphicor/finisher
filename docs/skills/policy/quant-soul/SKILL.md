---
name: quant-soul
type: policy
version: 1.3.1
triggers:
  - quant
  - trading
  - portfolio
  - backtest
  - sharpe
  - drawdown
  - transaction cost
  - slippage
  - methodology
  - CPCV
  - time-safety
applies_to:
  - scheme_agent
links:
  - docs/policies/quant_soul.md
  - docs/reference/quant_tech_stack.md
---

## Policy Skill: Quant Soul (Workflow + Hard Gates)

### Purpose

Enforce the **minimum, non-negotiable** standards for any scheme involving trading, portfolio construction, return/risk forecasting, or backtesting.

### What is binding vs reference

| Document | Role |
|----------|------|
| **`docs/policies/quant_soul.md`** | **Contract:** hard gates, evaluation workflow, artifact expectations. |
| **`docs/reference/quant_tech_stack.md`** | **Baseline training & patterns** (trees + NN habits): not Soul law, but skipping them usually prevents a **stable** baseline. |
| **`docs/reference/ide_execution_rules.md`** | **IDE session** behavior (SUBTASKS, EDA order, Override, glue style): loaded into **`core/ide_agent.py`** — not duplicated in the tech stack. |

Read Soul for **must**; read tech stack for **how** (e.g. *GBDT: fixed iterations*; *Supervised deep learning: epochs & baselines*; *Multiple labels / multi-target*); read **ide_execution_rules** for IDE execution agent specifics.

### Canonical policy

- The canonical policy document is `docs/policies/quant_soul.md`.
- This skill is a **wrapper** that makes the policy discoverable and injectable as a “policy skill”, and routes **implementation detail** questions to the tech reference when appropriate.

### When it applies

Apply when the task is quant-related (any of the triggers), especially when artifacts include:

- backtest design / evaluation protocol
- portfolio construction / weights / constraints
- transaction costs / slippage / capacity
- time-safety / leakage / point-in-time assumptions

### Enforcement semantics

- **Prompt injection (soft)**: the agent must see the policy text (or an excerpt) during scheme design.
- **Gate (hard)**: if any **Hard Gates** item from `docs/policies/quant_soul.md` is missing or violated, the scheme is **not executable**.

### Scheme phase vs execution acceptance

- **Scheme-phase artifacts** must name metric *families*, baselines, costs/constraints, and how pass/fail will be decided. They must **not** invent universal numeric cutoffs (Sharpe, turnover %, drawdown %) from templates; those are `provisional` until tied to data/mandate (`docs/policies/quant_soul.md` §5).
- **Exploration vs acceptance:** model selection and HPO use **time-safe train/val/test** — **not** CPCV combinatorics for exploration. **After** the model spec is **locked**, produce **acceptance** evidence per `quant_soul` §3 — **CPCV** is the **default** path but **not** the only admissible generalization protocol; **if you skip path-based CPCV**, you must still meet the **burden of proof** against overfitting (short validity horizons; “live months” alone is not enough). **Walk-forward / forward rolling** is **not** accepted (`ide_execution_rules` acceptance phasing).
- **RL:** training may be **mostly synthetic/sim**; **production** can follow when **real-data inference/execution** is **stable** under an explicit evaluation plan — see `quant_soul` §3 RL bullet + **`quant_tech_stack`** → **RL / Control** (not a loosening of metric honesty or time-safety).
- **Execution / model acceptance** is where diagnostics get concrete: protocol settings (CPCV or chosen alternative), cost model, and records such as `diagnostic_value` / `threshold` / `decision` for overfitting risk—when those are **locked**.

### Acceptance vs online deployment training

- A **documented acceptance protocol** (CPCV recommended by default) is the generalization gate for **online inference** models too, not only offline research.
- **After** acceptance, the **spec** is **locked**. Deployment weights **may** come from k-fold, path-based exports, or (under the same locked spec) a **full-history refit**—**without** new tuning on that refit run. **Material changes** require **new** acceptance evidence (`docs/policies/quant_soul.md` §3).
- NN retrain volatility and optional **online learning**: see **`docs/reference/quant_tech_stack.md`** → **Deployment refit after acceptance** (reference, not Soul law).

### Required evidence (minimum)

The scheme package must explicitly cover (can be concise, but must be explicit):

- time-safety assumptions (timestamps + no-lookahead)
- leakage/bias checklist (universe, survivorship, corporate actions)
- evaluation protocol (time-safe acceptance: default CPCV purge+embargo; alternatives allowed if justified in `quant_soul` §3; path-based OOS and per-path portfolio backtest as applicable; **not** walk-forward / forward rolling for acceptance or production)
- costs/constraints (tc/slippage + turnover/leverage/capacity)
- metrics + pass conditions (portfolio-level evidence, not only IC/R²; mandate-aligned objectives such as Sharpe/Calmar and explicit profile-dependent acceptance logic)
- for long/short-neutral designs, prioritize cost-adjusted return/volatility/Sharpe as primary acceptance dimensions; treat drawdown as guardrail unless mandate says otherwise
- prediction target and strategy objective alignment (explicit mapping from model output to tradable weights/signals)
- overfitting-risk fail-fast rule (if PBO/related diagnostics exceed threshold, reject/discard candidate and stop tuning that line)
- planning parameters must distinguish `provisional` (design-time) and `locked` (post data-analysis) status for CPCV/split settings used in acceptance.
- no universal hard caps for turnover/volatility/drawdown; acceptance logic must be mandate/profile specific and explicit.
- acceptance record includes explicit overfitting decision line: `diagnostic_value`, `threshold`, `decision`.

