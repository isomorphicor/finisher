---
name: promotion-decision-record
type: ops
version: 1.0.0
triggers:
  - promotion decision
  - promote to skill
  - decision record
applies_to:
  - repo
links:
  - docs/experiments/autonomous_research/templates/promotion_decision_record.md
  - docs/experiments/autonomous_research/workflow.md
  - scripts/check_repo_contract.py
---

## Ops Skill: Write a Promotion Decision Record

### Purpose

Create a consistent, auditable decision record for promoting an experiment into a stable skill.

### Steps

1. Copy the template:
   - `docs/experiments/autonomous_research/templates/promotion_decision_record.md`
2. Create a new record file next to the experiment you ran (recommended location):
   - `docs/experiments/autonomous_research/records/<YYYYMMDD>_<slug>.md`
3. Fill it with:
   - hypothesis, budget, run directory, artifacts, gate results
   - decision (Promote/Revise/Reject)
4. If you decided to promote:
   - add/update the target skill (`docs/skills/...` or `skills/...`)
   - update registries (`docs/skills/manifest.json` / `skills/registry/manifest.json`)
5. Run:
   - `python scripts/check_repo_contract.py`

### Verification

- The record contains concrete paths under `out/` for the evidence.
- Promotion changes are registered and pass the contract checker.

