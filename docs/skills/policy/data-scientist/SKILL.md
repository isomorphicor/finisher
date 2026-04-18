---
name: data-scientist
type: policy
version: 1.1.0
triggers:
  - data scientist
  - ETL
  - data dictionary
  - vendor data
  - crawler
  - lineage
  - data QA
  - features
  - data quality
  - data contract
applies_to:
  - scheme_agent
  - ide_execution_agent
  - repo
links:
  - docs/policies/cio.md
  - docs/policies/quant_soul.md
  - docs/roles/skill_contract.md
  - docs/skills/ops/research-orchestration/SKILL.md
---

## Policy Skill: Data Scientist (data path + dictionary)

### Purpose

Define the **capability surface** for the **data stage**: legal sourcing → reproducible, deliverable features, with **primary ownership of data quality acceptance**. This is a **skill lens**, not a separate org-chart role. Orchestration stays on the **CIO** thread; optional **Layer 1 / Layer 2** labels in `docs/agent/AGENTS.md` are shorthand only.

Data QA and the **data dictionary** exist to **support decision-grade conclusions**, not “EDA for its own sake” when the mandate is narrow ([`research-orchestration`](../ops/research-orchestration/SKILL.md)).

Downstream may proceed on “data usable” **within the stated contract and version**, and use **contract + version + QA records** to separate **data issues** from **model / protocol / execution** issues.

### Canonical policy / cross-links

- **`docs/policies/cio.md`** — single accountable thread (plan + execute).
- **`docs/policies/quant_soul.md`** — hard gates for quant schemes; assumptions and leakage disclosure at the data boundary are carried by **contract, dictionary, and reports** (not rewritten here).
- **`docs/roles/skill_contract.md`** — artifact ownership and anti-leakage splits where applicable.

### Responsibilities (summary)

1. **Sourcing strategy**: prefer **vendors** when cost, license, and coverage allow; use **compliant crawl / self-collection** as supplement, with **higher** cleaning and QA burden on this layer.
2. **Legality & provenance**: only **lawfully obtained** data; document **source type** (vendor / crawl / self-collected) and license boundaries.
3. **Pipelines**: ETL, EDA, catalog, **versioning & lineage**; monitor **drift** when feeds are long-lived.
4. **Cleaning & alignment**: auditable process and **disclosed quality level** — not a promise of perfect zero-defect data.
5. **Features**: for downstream modeling/backtest; business logic and WQ-style mining are allowed if **legal and auditable**.
6. **Data dictionary**: after **secondary processing** (cleaning, transforms, derived fields), deliver an **updated dictionary** (semantics, types, units, timezone, availability, mapping to upstream, missingness rules, etc.) so downstream can align on semantics without guessing.

### Trust model

- **“Usable by default”** means usable **within** that version’s **data contract + QA report + version/hash** — not mathematical perfection.
- **Acceptance**: data QA is **owned here**; downstream does **not** substitute for data acceptance but **should feed back** issues; fix ownership stays on the data side.
- **Vendor path**: baseline on vendor package; still run analysis, spot checks, invariants; produce a **rigorous data QA report** (method, scope, conclusions, **residual risk**).
- **Crawl / self-collect**: dirtier; do **not** claim vendor-like implicit stability; document **limitations and bad cases**; goal is **usable within disclosure**, traceable iteration.

### Required deliverables (minimum)

- **Data dictionary** covering all **externally exposed** fields/tables after processing.
- **Data contract** (may merge with dictionary): sample bounds, universe, availability timestamps, etc., aligned with downstream.
- Feature notes, EDA/QA highlights, lineage, **version identity**; bridge to **`quant_soul`** leakage/assumption disclosure via **contract + dictionary + reports**.

### Boundaries (what this skill does not own)

- **Does not** own modeling **acceptance criteria** or backtest **protocol design** (Quant Researcher).
- **Does not** own backtest/trading **engineering integration** or live execution plumbing (Quant Dev; this repo **does not** emphasize live trading as default).

**Tool-skill note:** Where work is implemented as **deterministic tool skills**, **Layer 1** vs **Layer 2** ownership follows **`docs/roles/skill_contract.md`** §§8–9. This policy skill describes **data-path deliverables** (contracts, dictionary, QA); it does **not** override anti-leakage rules in code.

### What this skill owns

Legal sources, processing, dictionary, versioning, **data-side QA**, and **attribution anchors** for data-layer issues.
