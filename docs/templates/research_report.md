# Research report (template)

Copy sections into `project/outputs/` (or your deliverable path). Goal: **user-trusted** conclusions without requiring a **source code audit** — evidence, limitations, and reproducibility are explicit.

---

## 1. Executive answer (≈1 page)

**Question (mandate):** …

**Answer in one paragraph:** …

**Decision relevance:** What should the user **do** or **believe** differently, given evidence (or: **insufficient evidence** — what is missing)?

**Confidence:** High | Medium | Low — **why** (data span, protocol, single vs multi-path evidence).

---

## 2. Evidence appendix

### 2.1 Data & setup

- Data sources, versions, universe, date range.
- Key joins / keys (e.g. date, instrument id); time-safety statement ([`quant_soul`](../policies/quant_soul.md)).

### 2.2 Methods (minimal sufficient)

- Models, splits, **exploration vs acceptance** protocol (if both).
- Hyperparameters or “defaults + why.”

### 2.3 Results (honest names)

- Tables/paths to `outputs/` artifacts; metrics **match** code ([`ide_core_rules`](../reference/ide_core_rules.md) R-line).

### 2.4 Related work / literature (if used)

- What was retrieved ([`information-collection`](../skills/ops/information-collection/SKILL.md)); how it **constrains** or **contrasts** with your empirical result — not decoration.

---

## 3. Limitations & scope

- What was **not** tested (regimes, labels, costs sensitivity).
- **Exploratory** vs **confirmatory** — avoid over-claiming from multiple testing ([`cognitive-research-flow`](../skills/ops/cognitive-research-flow/SKILL.md)).

---

## 4. Negative / null results

- What hypotheses were **ruled out** or **not supported** — valuable outputs.

---

## 5. Reproducibility bundle

| Item | Value |
|------|--------|
| Environment | Python version, key packages |
| Commands | Exact CLI or script entrypoints |
| Inputs | Paths to data/config |
| Outputs | Paths to metrics JSON/CSVs |
| Seeds | If stochastic |

User should be able to **re-run** without reading `src/` line-by-line.

---

## 6. Adversarial pass (“what breaks this?”)

- Short paragraph: strongest **counter-evidence** or **failure mode** that would **change** the executive answer.

---

## 7. Conflicts / incentives (optional)

- Data vendor bias, incentive to show positive Sharpe, etc., if relevant.

---

## 8. Mandate drift (if any)

If the question **changed** mid-run, **re-state** the final mandate before conclusions.
