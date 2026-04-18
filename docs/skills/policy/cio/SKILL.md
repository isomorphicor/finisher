---
name: cio
type: policy
version: 1.5.0
triggers:
  - CIO
  - orchestrator
  - fund manager
  - portfolio manager
  - mandate
  - acceptance
  - sign-off
applies_to:
  - scheme_agent
  - ide_execution_agent
  - repo
links:
  - docs/policies/cio.md
  - docs/agent/AGENTS.md
  - docs/experiments/scheme_phase/blueprint.md
  - docs/roles/skill_contract.md
  - docs/skills/ops/research-orchestration/SKILL.md
---

## Policy Skill: CIO (Project Soul)

### Purpose

Anchor work on the **CIO charter**: **CIO agent** (thinking/scheduling) **directs** **execution agents**; **global view** + **core-rule veto** + **flexible** non-core defaults (`quant_tech_stack`, `knowledge/`) with audit trail — see **`docs/policies/cio.md`** § **CIO judgment: global view, core rules, and flexibility**. **Human** may remain ultimate authority.

**Mandate and resources** are owned with the **user**; **task decomposition** (which phases, which skills from [`manifest.json`](../../manifest.json)) is **agent** responsibility unless the user specifies a fixed recipe. Success is **conclusion quality + evidence** per mandate — **not** “user must review every line of `project/src/`.” See [`research-orchestration`](../research-orchestration/SKILL.md) and [`docs/templates/research_report.md`](../../../templates/research_report.md).

This project does **not** treat human buy-side departmental boundaries as a template; optional **Layer 1 / Layer 2 / Reviewer** labels in `AGENTS.md` are lenses, not org-chart seats.

### Canonical policy

- **`docs/policies/cio.md`** — full charter (**Unified operating model**, **Event-driven handoff**, **CIO judgment** § core vs flexibility).
- **`docs/agent/AGENTS.md`** — CIO as the default interface; optional labels map to MD policy skills; not mandatory splits.
- **`docs/experiments/scheme_phase/blueprint.md`** — sector ↔ minimal artifacts ↔ gates table (scheme phase).

### When it applies

Apply when framing tasks, autonomy, multi-agent orchestration, or “who decides” — scheme phase, IDE sessions, or **meta-loops** that alternate CIO review with worker runs.

### Relationship to quant gates

- **CIO** decides priorities and whether outputs meet the mandate.
- **`docs/policies/quant_soul.md`** defines **hard gates** for quant-related schemes (separate from this orchestration soul).
- **`docs/reference/quant_tech_stack.md`** and **`knowledge/`** supply technique and long-term context for the CIO-led agent to use.

### Capability skills (stage lenses, not separate agents)

Implementation work is routed through **policy skills** that match the data / research / engineering split. The CIO thread **calls** these as contracts; it does **not** simulate a buy-side org chart. For **MD policy skills vs Python tool layers**, see **`docs/roles/skill_contract.md`** §§5–6 vs §8.

| Skill | Path | One-line scope (normative summary) |
|-------|------|-----------------------------------|
| **Data Scientist** | `docs/skills/policy/data-scientist/SKILL.md` | Legal sourcing → dictionary/contract/QA/versioned features; tool code obeys **Layer 1** vs **Layer 2** in `skill_contract` §8. |
| **Quant Researcher** | `docs/skills/policy/quant-researcher/SKILL.md` | Hypothesis → modeling → evidence; **`quant_soul`** when quant-related; **stage-only** topics need not ship full tradable weights unless the mandate is closed-loop. |
| **Quant Dev** | `docs/skills/policy/quant-dev/SKILL.md` | Backtest/sim, venue adapters (paper/sim/test), signal→order plumbing, non-research ops; **not** live desk as default; maps **closed-loop tradable specs** or **stage interfaces** to runnable software. |
| **Quant Soul** | `docs/skills/policy/quant-soul/SKILL.md` | Wrapper for **`docs/policies/quant_soul.md`** hard gates (orthogonal to CIO orchestration). |

Related: **`docs/agent/AGENTS.md`** (stage-only vs closed-loop), **`docs/experiments/scheme_phase/blueprint.md`** (sector table).
