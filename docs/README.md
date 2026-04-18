# Documentation Index

Scheme phase is the current runnable focus. Keep docs minimal and operational.

---

## Principles vs knowledge base

| | |
|--|--|
| **Core principles (short)** | [**principles/README.md**](principles/README.md) — headlines + links; read first |
| **Depth / lessons** | [**knowledge/README.md**](../knowledge/README.md) (repo root `knowledge/`) |

---

## Flat map (avoid nested “see X → Y → Z”)

| Goal | Start here | Only if needed |
|------|------------|----------------|
| **CIO agent ↔ execution agents** (orchestration, event handoff) | [**policies/cio.md**](policies/cio.md) | [**agent/AGENTS.md**](agent/AGENTS.md) |
| **IDE agent** (session `project/`) | [**reference/ide_core_rules.md**](reference/ide_core_rules.md) | [**ide_execution_rules.md**](reference/ide_execution_rules.md) (appendix), [**quant_soul.md**](policies/quant_soul.md) (gates), [**quant_tech_stack.md**](reference/quant_tech_stack.md) (models) |
| **Scheme phase** (design artifacts) | [**experiments/scheme_phase/blueprint.md**](experiments/scheme_phase/blueprint.md) | same doc’s gates table; [**skills/**](skills/) by name |

Do **not** treat `contracts/`, `guides/`, `policies/`, and `reference/` as a mandatory tour — open **one** file from the “Only if needed” column.

---

## Start here

| Doc | Purpose |
|-----|---------|
| [**experiments/scheme_phase/blueprint.md**](experiments/scheme_phase/blueprint.md) | Scheme phase: how to run + required artifacts + gates + **sector ↔ artifact ↔ gate** table |
| [**experiments/autonomous_research/blueprint.md**](experiments/autonomous_research/blueprint.md) | Self-iterating loop: experiment → evidence → promotion |
| [**agent/**](agent/) | Agent contracts: operating loop, memory, roles, values, user prefs |
| [**DEVELOPMENT_CONTRACT.md**](DEVELOPMENT_CONTRACT.md) | Single source of truth for repo evolution (taxonomy, skills, anti-drift) |
| [**skills/**](skills/) | MD skills (policy + ops), registry (`manifest.json`), templates — includes **cio**, **quant-soul**, **data-scientist**, **quant-researcher**, **quant-dev** |
| [**project_status.md**](project_status.md) | Status and near-term goals |
| [**worklog.md**](worklog.md) | Minimal change log (only key behavior changes) |
| [**guides/skill_catalog.md**](guides/skill_catalog.md) | Tool skills and deterministic post-processing |
| [**guides/command_examples.md**](guides/command_examples.md) | Practical CLI examples; **`scripts/run_research_session.py`** (or `run_scheme_then_ide.py`) = scheme + IDE in one command |
| [**skills/ARCHITECTURE.md**](skills/ARCHITECTURE.md) | Skill layers L0–L3, L2 runtime mapping, deprecated `run_autonomy_loop` |
| [**reference/ide_core_rules.md**](reference/ide_core_rules.md) | **IDE: default rules** (embedded); **§ A–D** = business, compute, baselines, generalization — **no doc chain required** |
| [**reference/ide_execution_rules.md**](reference/ide_execution_rules.md) | **IDE appendix** (tiers, combinatorics, Override wording); optional prompt chunk via `ide_execution.ide_rules_profile: extended` |
| [**guides/ide_execution_phases.md**](guides/ide_execution_phases.md) | IDE agent: **phased workflow** (EDA → load → train), **minimum viable EDA**, round discipline |
| [**guides/ide_context_budget.md**](guides/ide_context_budget.md) | **Prompt size** vs local models: `INVERST_IDE_SKILLS=compact`, scheme caps |
| [**plans/ide_execution_long_running.md**](plans/ide_execution_long_running.md) | **(Planned)** Long-running IDE execution agent: checkpoint, resume, context limits — **after experiment phase** |
| [**skills/ops/session-project-code/SKILL.md**](skills/ops/session-project-code/SKILL.md) | Session `project/` **paths & hardware** (MPS/CatBoost); IDE defaults in **`reference/ide_core_rules.md`** + extended **`ide_execution_rules.md`** |
| [**templates/execution_report_ide.md**](templates/execution_report_ide.md) | IDE execution agent: **`execution_report.md`** structure + baseline training contract checklist |
| [**templates/knowledge_promotion_checklist.md**](templates/knowledge_promotion_checklist.md) | Session → **`knowledge/`** promotion gates (what to log, where, anti-patterns) |
| [**knowledge/ide_lessons.md**](../knowledge/ide_lessons.md) | Promoted IDE/session lessons (append-only; not a copy of every run) |

---

## Reference

**CIO / agent / quant / IDE** — use the **Flat map** table above; avoid reading every link in this section in order.

**Contracts and standards:** [contracts/](contracts/), [guides/](guides/), [roles/skill_contract.md](roles/skill_contract.md) (policy vs tool layers).

**CIO charter:** [policies/cio.md](policies/cio.md).
**Agent contract:** [agent/AGENTS.md](agent/AGENTS.md).
**Quant hard gates:** [policies/quant_soul.md](policies/quant_soul.md).
**Quant tech stack:** [reference/quant_tech_stack.md](reference/quant_tech_stack.md).
**IDE:** [reference/ide_core_rules.md](reference/ide_core_rules.md) · appendix [reference/ide_execution_rules.md](reference/ide_execution_rules.md).
**Global knowledge layer:** [reference/agent_knowledge_system.md](reference/agent_knowledge_system.md).

**Autonomy (code):** `core/scheme_agent.py` (refine + structure/keyword/topic gates; optional `scheme_summary.json` and `experiment_matrix.json`), `core/refine.py` (refine_user_need_to_task), `core/experiment_matrix.py` (deterministic matrix builder), `skills/scheme_phase.py` (tool skills), `scripts/run_scheme_agent.py` (CLI entry).
**Archived:** [archive/research_testcase.md](archive/research_testcase.md)
