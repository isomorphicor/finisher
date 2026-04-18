---
name: research-orchestration
type: ops
version: 1.1.0
triggers:
  - orchestration
  - research plan
  - mandate
  - phase order
  - full-stack
  - slice
  - EDA first
  - explore before scheme
applies_to:
  - scheme_agent
  - ide_execution_agent
  - repo
links:
  - docs/skills/README.md
  - docs/skills/ARCHITECTURE.md
  - docs/skills/manifest.json
  - docs/skills/ops/cognitive-research-flow/SKILL.md
  - docs/skills/ops/manual-supervisor-playbook/SKILL.md
  - docs/skills/ops/scheme-phase/SKILL.md
  - docs/policies/cio.md
---

## Ops Skill: Research orchestration (task planner)

### Purpose

Provide a **decision-centric** playbook for **which research phases to run and in what order**, given a **user mandate** and **available resources**. This is **judgment under policy**, not a substitute for [`docs/policies/quant_soul.md`](../../../policies/quant_soul.md) or other hard gates.

**Non-goals:** This skill does **not** mandate a single CLI entrypoint. The linear pipeline `scheme → prep → IDE` ([`core/research_session_pipeline.py`](../../../core/research_session_pipeline.py)) is **one** tested composition (good for end-to-end integration). **Narrow mandates** may only need a subset of capabilities — see **Mandate classes** below.

### Inputs (clarify before heavy spend)

1. **Mandate** — question, success definition, horizon, risk constraints.
2. **Resources** — data access, compute, time to decision, APIs (literature search is available via scheme tools; see [`information-collection`](../information-collection/SKILL.md)).
3. **Acceptance depth** — exploration-only vs locked protocol vs full acceptance evidence ([`quant_soul`](../../../policies/quant_soul.md)).

### Mandate classes

| Class | Typical sequence | Stop when |
|-------|------------------|-----------|
| **Full-stack** | Info retrieval → EDA/probe → scheme lock → implementation → acceptance diagnostics | Evidence answers mandate per `quant_soul` / experiment design |
| **Slice: literature** | Paper search + synthesis memo | Reviewable bibliography + implications; no fabricated backtests |
| **Slice: data / EDA** | Explore-only IDE ([`--explore-only`](../../../scripts/run_ide_execution_agent.py)) or probes → `eda_report.md` | Data trust + dictionary updates; mandate may stop here |
| **Slice: modeling smoke** | Probe on one label/period ([`cognitive-research-flow`](../cognitive-research-flow/SKILL.md)) | Direction locked or hypothesis falsified |
| **Scheme-first** | Mandate crisp; data contract known — lock [`scheme-phase`](../scheme-phase/SKILL.md) artifacts then implement | Artifacts + downstream IDE |

**Anti-pattern:** Success = “files exist” or “code written” **without** a **stated conclusion** traceable to evidence. **Anti-pattern:** Running full **scheme → IDE** when the user only asked for a literature memo.

### Phase-order heuristics

- **EDA / explore before scheme** when: schema unknown, wide panel I/O risk, or mandate still fuzzy — use exploration IDE or probes first; feed findings into scheme task text.
- **Scheme-first** when: mandate and data contract are clear; bottleneck is **locked** experiment design and acceptance protocol.
- **Implementation-first smoke** when: cheap falsification on a slice is enough to pivot ([`cognitive-research-flow`](../cognitive-research-flow/SKILL.md)).

### Relation to linear CLI

- [`scripts/run_research_session.py`](../../../scripts/run_research_session.py) runs **scheme → prep → IDE** (optional **`--explore-before-scheme`** to run exploration IDE first). Use it when the mandate matches that composition.
- Otherwise compose **stepwise** (`run_scheme_agent`, `run_ide_execution_agent`, …) per rows in [`ARCHITECTURE.md`](../../ARCHITECTURE.md) L2 table — see [`manual-supervisor-playbook`](../manual-supervisor-playbook/SKILL.md) for a checklist.

### Runtime flags (quick reference)

| Situation | Flag / env |
|-----------|------------|
| EDA / probes; `artifacts/*.md` may be missing | `run_ide_execution_agent` **`--explore-only`** or `INVERST_IDE_EXPLORATION=1` |
| Exploration IDE **before** scheme in one pipeline | `run_research_session.py` **`--explore-before-scheme`** (optional default task when `--ide-task` empty) |
| SUBTASKS/DONE must not auto-close the run | **`--iteration`** / `INVERST_IDE_ITERATION=1` |
| Task JSON (`core/task_runners.py` mode `ide_execution_agent`) | Optional keys **`iteration_mode`**, **`exploration_mode`** (`true`/`false`; omit for env defaults) |

### Verification

- [ ] Mandate class identified (full-stack vs slice).
- [ ] Stopping rule explicit (“enough for this question”).
- [ ] No unmotivated full grid before probe ([`cognitive-research-flow`](../cognitive-research-flow/SKILL.md)).

### Rollback

N/A — playbook only. Re-scope mandate and re-run.
