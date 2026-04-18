---
name: autonomous-research-loop
type: ops
version: 1.0.0
triggers:
  - autonomous research
  - self-iterating agent
  - promote experiment to skill
applies_to:
  - repo
links:
  - docs/experiments/autonomous_research/blueprint.md
  - docs/experiments/autonomous_research/workflow.md
  - docs/skills/manifest.json
  - scripts/check_repo_contract.py
---

## Ops Skill: Autonomous Research Loop (Experiment → Skill)

### Purpose

Run autonomy experiments in a bounded way and **promote only accepted results** into reusable skills, so the repo improves without architecture drift.

### Preconditions

- You can run the repo’s primary entrypoint (`scripts/run_scheme_agent.py`) or any other agreed experiment runner.
- You will store evidence under `out/` (ephemeral but auditable by path).

### Steps

1. **Define hypothesis + budget + triggers**

2. **Run the bounded experiment**
   - Prefer skill-first entries: `python scripts/run_research_session.py` or `run_scheme_then_ide.py` for full-stack runs; or stepwise `run_scheme_agent` / `run_ide_execution_agent` per [`research-orchestration`](../research-orchestration/SKILL.md).
   - Legacy: `python scripts/run_scheme_agent.py --model <MODEL> --lang en "<task>"`

3. **Collect evidence**
   - Keep the run directory (e.g. `out/<project>/<session>/artifacts/`)
   - Identify which artifacts/gates support the hypothesis

4. **Decide** (promote/revise/reject) using a promotion decision record

5. **Promote**
   - Workflow/playbook → create `docs/skills/ops/<name>/SKILL.md`
   - Constraints/gates → create `docs/skills/policy/<name>/SKILL.md` + link canonical docs
   - Deterministic execution → create Python skill under `skills/` and register it

6. **Register + enforce**
   - Add the new MD skill to `docs/skills/manifest.json`
   - Run: `python scripts/check_repo_contract.py`

### Verification

- Contract checker passes (`Repo contract check: OK`)
- The new skill is discoverable (present in `docs/skills/manifest.json`)
- Links in docs point to canonical experiment specs and policies

