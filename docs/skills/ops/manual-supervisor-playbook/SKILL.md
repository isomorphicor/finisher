---
name: manual-supervisor-playbook
type: ops
version: 1.0.0
triggers:
  - supervisor
  - manual orchestration
  - compose entrypoints
  - L2 selection
  - stepwise research
applies_to:
  - scheme_agent
  - ide_execution_agent
  - repo
links:
  - docs/skills/ops/research-orchestration/SKILL.md
  - docs/skills/ARCHITECTURE.md
  - docs/policies/cio.md
  - core/research_session_pipeline.py
---

## Ops Skill: Manual supervisor playbook (no Python loop)

### Purpose

**Phase 3** in [`ARCHITECTURE.md`](../../ARCHITECTURE.md) calls for a *supervisor* that selects among **L2** entrypoints. This repo does **not** ship an automated supervisor process yet. This skill is the **stand-in**: a short checklist so a **human or tool-using agent** composes runs **deliberately** — aligned with [`research-orchestration`](../research-orchestration/SKILL.md) and [`docs/policies/cio.md`](../../../policies/cio.md).

**Non-goals:** Replace policy gates, scheme quality bars, or IDE rules. Do not treat this as permission to skip evidence or mandated artifacts.

### Preconditions

- Mandate class chosen (full-stack vs slice) per [`research-orchestration`](../research-orchestration/SKILL.md).
- Session path convention understood: `<runs_root>/<project>/<session>/` (see [`core/scheme_paths.py`](../../../../core/scheme_paths.py)).

### Steps

1. **Classify the ask** — literature-only, EDA-only, scheme lock + build, or full acceptance path. Write a one-line **stopping rule** (“enough when …”).

2. **Map to L2 (pick one primary path; add branches only if mandate needs them)**

   | Goal | Typical entry | Notes |
   |------|----------------|-------|
   | Literature / related work | Scheme phase tools (`paper_search`) or batch via scheme task | No fabricated backtests ([`information-collection`](../information-collection/SKILL.md)). |
   | EDA / data dictionary without full scheme | `run_ide_execution_agent` + **`--explore-only`** | Missing `artifacts/*.md` OK; no CPCV / production claims ([`data-first-execution`](../data-first-execution/SKILL.md)). |
   | Full-stack in one process | `run_research_session.py` / `run_scheme_then_ide.py` | Optional **`--explore-before-scheme`** for probes before scheme lock ([`research_session_pipeline.py`](../../../../core/research_session_pipeline.py)). |
   | Scheme package only | `run_scheme_agent` | Artifacts under `<session>/artifacts/`. |
   | Implement after scheme | `prepare_execution_workspace` (optional) + `run_ide_execution_agent` | Normal mode expects **four** scheme artifacts present. |
   | Follow-up IDE without re-scheming | `run_ide_execution_agent` + **`--iteration`** if SUBTASKS/DONE must not auto-close the run | Env: `INVERST_IDE_ITERATION=1`. |

3. **Compose flags** — prefer explicit CLI over env when documenting a repro bundle. Exploration env mirror: `INVERST_IDE_EXPLORATION=1` ≈ `--explore-only`.

4. **Record** — append a line to `docs/worklog.md` (or session `project/outputs/WORKLOG` if used) when behavior or entrypoint choice changes how others must run the repo.

### Verification

- [ ] Mandate class and stopping rule are explicit.
- [ ] Chosen entrypoint matches **resources** (data paths, time, compute) — no unmotivated full pipeline for a slice ask.
- [ ] Exploration vs acceptance **language** matches mode (explore-only / explore-before-scheme vs locked scheme + diagnostics).

### Rollback

Re-scope the mandate; discard or archive the session folder if the wrong path was chosen; re-run from step 1.

### Related

- Automated multi-chunk supervisor / CIO loop — **not** in scope here; see [`docs/plans/ide_execution_long_running.md`](../../../plans/ide_execution_long_running.md) for engineering direction.
