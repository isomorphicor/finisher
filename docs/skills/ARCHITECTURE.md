# Skill architecture (L0–L3)

This document defines how **policy skills**, **ops playbooks**, **runtime capabilities**, and **meta** workflows fit together. It aligns with the skill-first research direction: **orchestration lives in the agent + tools**, not in thick outer Python loops.

**Start here for intent:** [`README.md`](README.md) (mandate + resources → conclusions). **Task ordering (full-stack vs slice):** [`ops/research-orchestration/SKILL.md`](ops/research-orchestration/SKILL.md).

## Orchestration philosophy

- **Scheme design**, **EDA / exploration**, **modeling / implementation**, and **information collection** (e.g. literature) are **peer capabilities**. The **default order is mandate-driven**, not “always scheme first.”
- **Linear pipeline** — `python scripts/run_research_session.py` runs **scheme → prep → IDE** ([`core/research_session_pipeline.py`](../core/research_session_pipeline.py)); optional **`--explore-before-scheme`** runs an **exploration IDE** pass first. That composition is ideal for **end-to-end integration** and full-stack mandates; it is **not** the only valid way to do research (see [`research-orchestration`](ops/research-orchestration/SKILL.md)).

## Non-linear execution

- **L2** entries below are **capabilities** (callable or invokable tools). A **supervisor** (human, future meta-agent, or documented manual plan) **selects** which to run and when — see **Phase 3 roadmap** at the end of this file.
- **Skill catalog:** [`manifest.json`](manifest.json) is the **menu** of MD skills; combine with L2 for a concrete plan.

## Layers

| Layer | Role | Location | Consumed by |
|-------|------|----------|-------------|
| **L0 Policy** | Norms, acceptance language, role contracts | `docs/skills/policy/*/SKILL.md` | Scheme/IDE system prompts, human review |
| **L1 Ops** | Repeatable playbooks: steps, verification, rollback | `docs/skills/ops/*/SKILL.md` | Humans and agents following a checklist |
| **L2 Runtime** | Callable behavior tied to Python entrypoints | `core/` (e.g. `run_scheme_agent`, `run_ide_execution_agent`, `revise_scheme_session`) | CLIs and future unified tool surfaces |
| **L3 Meta** | Promotion, new-skill scaffolding, repo hygiene | `docs/skills/ops/autonomous-research-loop/`, `add-python-skill/`, … | Maintainers |

Registry: [`manifest.json`](manifest.json) (`md_skill_registry_v1`).

## L2 mapping (runtime “skills”)

These are the **code anchors** for research execution capabilities:

| Capability | Primary API | Notes |
|------------|-------------|--------|
| Scheme design | `run_scheme_agent` (+ scheme phase tools, e.g. `paper_search`) | Artifacts under `<session>/artifacts/` |
| Execution prep | `prepare_execution_workspace` | Syncs scheme → `project/` for IDE |
| IDE / coding | `run_ide_execution_agent` | Tools: terminal, workspace write; **`--explore-only`** for EDA without full scheme artifacts |
| Exploration | Same as IDE | Exploration mode: probes, `eda_report.md` — **no** acceptance/CPCV claims until scheme package exists |
| Package review | `review_scheme_package` | JSON review; optional gate before heavy IDE |
| Scheme revision | `revise_scheme_session` | Feedback-driven edits to artifacts |
| Literature (backend) | [`core/paper_search.py`](../core/paper_search.py) | Used by scheme tools; see [`ops/information-collection`](ops/information-collection/SKILL.md) |

**Recommended CLIs:**

- `python scripts/run_research_session.py` — skill-first **full-stack** entry (optional `--explore-before-scheme`).
- `python scripts/run_scheme_then_ide.py` — same pipeline, legacy-friendly name.
- **Stepwise:** `run_scheme_agent` / `run_ide_execution_agent` / … per mandate ([`research-orchestration`](ops/research-orchestration/SKILL.md)).

Shared implementation: [`core/research_session_pipeline.py`](../core/research_session_pipeline.py).

**Deprecated:** `scripts/run_autonomy_loop.py` — do not extend; use the entries above.

## Phase 3 roadmap (supervisor)

**Intent:** Something selects among L2 entrypoints — scheme-only, IDE-only, explore-only, literature batch — based on **mandate + resources**, aligned with [`docs/policies/cio.md`](../policies/cio.md) and [`research-orchestration`](ops/research-orchestration/SKILL.md).

| Stage | Status | What it is |
|-------|--------|------------|
| **3a — Linear compositions** | **In repo** | `run_research_session.py` / `run_scheme_then_ide.py` (`scheme → prep → IDE`); optional [`--explore-before-scheme`](../../core/research_session_pipeline.py). Standalone explore: `run_ide_execution_agent` + `--explore-only` / `INVERST_IDE_EXPLORATION`. |
| **3b — Manual supervisor** | **In repo (docs)** | [`ops/manual-supervisor-playbook/SKILL.md`](ops/manual-supervisor-playbook/SKILL.md) — checklist for humans/agents composing stepwise runs without a Python supervisor loop. |
| **3c — Automated supervisor** | **Prototype (narrow)** | [`scripts/run_supervisor_ide.py`](../../scripts/run_supervisor_ide.py) + [`core/supervisor_ide_loop.py`](../../core/supervisor_ide_loop.py) — chunked **text CIO** + IDE; model ids via [`resolve_supervisor_cio_model`](../../core/ide_execution_config.py) + `settings.llm`. **Not** a full L2 picker or checkpoint resume; see [`ide_execution_long_running.md`](../plans/ide_execution_long_running.md). |

Default orchestration remains **manual composition** (3b) or **linear CLI** (3a); use **3c** when you want staged CIO + IDE in one process.

## Authoring checklist (new SKILL.md)

1. **Frontmatter:** `name`, `type` (`policy` | `ops`), `version`, `triggers`, `applies_to`, `links`.
2. **Register** in [`manifest.json`](manifest.json) with a stable `id` (`policy.*` / `ops.*`).
3. **Ops skills:** follow [`templates/ops_skill_template/SKILL.md`](templates/ops_skill_template/SKILL.md) — Purpose, Preconditions, Steps, Verification, Rollback.
4. **Policy skills:** follow [`templates/policy_skill_template/SKILL.md`](templates/policy_skill_template/SKILL.md); must not contradict `docs/policies/*.md`.
5. **Do not** reference deprecated scripts (`run_autonomy_loop.py`) in Steps; use `run_research_session.py` / `run_scheme_then_ide.py` or stepwise `run_scheme_agent` + `run_ide_execution_agent`.

## Related

- [`docs/skills/README.md`](README.md) — charter and catalog pointer.
- [`docs/principles/README.md`](../principles/README.md) — **core principles (terse)** vs **knowledge base** depth (`knowledge/`).
- [`docs/policies/cio.md`](../policies/cio.md) — orchestration intent vs execution.
- [`docs/plans/ide_execution_long_running.md`](../plans/ide_execution_long_running.md) — checkpoint / long sessions (engineering; not a second business loop).
