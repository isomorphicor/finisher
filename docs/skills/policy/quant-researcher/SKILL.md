---
name: quant-researcher
type: policy
version: 1.1.0
triggers:
  - quant researcher
  - hypothesis
  - labeling
  - model acceptance
  - OOS
  - portfolio weights
  - backtest protocol
  - CPCV
  - research
  - factor
  - reward
applies_to:
  - scheme_agent
  - ide_execution_agent
  - repo
links:
  - docs/policies/quant_soul.md
  - docs/reference/quant_tech_stack.md
  - docs/policies/cio.md
  - docs/roles/skill_contract.md
  - docs/skills/ops/research-orchestration/SKILL.md
  - docs/templates/research_report.md
---

## Policy Skill: Quant Researcher (research + modeling)

### Purpose

Define the **capability surface** for **hypothesis → modeling object (labels/features/algorithms) → experiments → acceptance evidence**, built on the Data Scientist’s **dictionary and versioned data/features**. For any quant backtest/portfolio work, **`quant_soul`** is binding; concrete techniques are guided by **`quant_tech_stack`** (non-binding catalog). Orchestration remains **CIO**; this skill is **not** a separate agent thread.

This is a **reasoning lens** for any agent that produces research artifacts (scheme, IDE, or future supervisor) — not only the scheme-phase LLM.

### Decision deliverables (user-trusted conclusions)

Primary success is **written conclusions + evidence**, not source-code review by the user:

1. **Falsifiable hypotheses** and what would **refute** them.
2. **Evidence chain** (data → method → metric) with **honest names** matching computation.
3. **Actionable implications** for the mandate when in scope; **limits** and **what would change the recommendation** when evidence is weak or exploratory.
4. **Reproducibility pointers** (commands, paths, env) — see [`docs/templates/research_report.md`](../../templates/research_report.md); code exists to **re-run**, not as the main audit surface.

### Canonical policy / cross-links

- **`docs/policies/quant_soul.md`** — workflow, hard gates, acceptance (contract).
- **`docs/reference/quant_tech_stack.md`** — technique choices and patterns (reference, not a substitute for Soul).
- **`docs/policies/cio.md`** — mandate and single-owner thread.
- **`docs/roles/skill_contract.md`** — artifact boundaries where relevant.

### Output shapes (do not one-size-fits-all)

- **Investment-closed-loop / portfolio-facing**: deliverables should tend toward **backtestable, executable** instructions (e.g. **target weights**, **target positions**, or equivalent transforms). Fix **interfaces** (universe, normalization, how constraints enter weights). Training/ diagnostic metrics (MSE, IC, …) must chain **→ tradable object → portfolio evaluation**; **do not** accept IC/R²/MSE alone. Acceptance follows **`quant_soul`** portfolio-level evidence **including costs and constraints**. Loss tuning without a **tradable edge** story should not be the main success criterion.
- **Stage-only topics** (one link in the chain): e.g. feature/representation work, **new labels**, algorithms, training strategies, theory subproblems — **full tradable weights are not required** for that topic alone. Deliver **reproducible results + boundaries** (I/O semantics, **upstream/downstream interfaces**; if not yet combined into a portfolio, **state how** to close the loop to tradable evaluation). When backtests apply, still meet **`quant_soul`** gates relevant to the topic (time-safety, leakage, evaluation protocol).

### Research process

Open-ended problems; **pose falsifiable questions**, **record negative results** (see `knowledge/failure_patterns` if present), **version** topic/label changes; literature is **comparison**, not a template. **Exploration budget** is separate from **acceptance protocol**. Novelty **does not** waive **`quant_soul`**.

### Relationship to Data Scientist

- **EDA**: DS = **data trust + dictionary**; QR = **modeling-oriented** (feature–label, stability, regime, horizon, outliers vs loss).
- **Boundary**: trust semantics within the agreed version; **data QA primary DS**; **labels** consistent with market semantics; **no modeling leakage**; **universe** changes → **artifact versioning**.

### Responsibilities (summary)

1. Testable questions, meaning of labels/topics, **why different from a template**.
2. **Acceptance-grade** evaluation per **`quant_soul`** for **quant-related** work (policy text + topic scope); other topics follow the mandate’s gates only.
3. Exploration vs acceptance separation; `provisional` / `locked`, DoF, pass rules.
4. **If the mandate is investment-closed-loop:** auditable **proxy ↔ tradable output ↔ portfolio utility**, plus **Quant Dev**-ready specs when execution engineering is in scope. **If the mandate is stage-only** (e.g. new label, feature mining, algorithm): deliver **reproducible stage artifact + interfaces**; **no** requirement to ship full tradable weights in the same topic unless the mandate says so.
5. Overfitting diagnostics; **fail-fast** beyond threshold.

### Required deliverables (minimum)

Reproducible writeup, **locked** acceptance config where applicable, OOS/path summary if applicable, **self-check aligned to `quant_soul`** (trimmed to topic), overfitting decision line. **Investment-closed-loop topics** additionally: **tradable interface** description. **Does not** replace the **data dictionary**.

### Boundaries

- **Does not** own ETL / **primary data dictionary** ownership.
- **Owns** research conclusions and **interface/spec** by topic type (including tradable side when in closed-loop), and **version + dictionary** alignment when disputing DS.
