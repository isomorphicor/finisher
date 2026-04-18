---
name: scaffold-promotion-record
type: ops
version: 1.0.0
triggers:
  - scaffold promotion record
  - new promotion record
  - promotion record template
applies_to:
  - repo
links:
  - docs/experiments/autonomous_research/templates/promotion_decision_record.md
  - docs/experiments/autonomous_research/records/README.md
---

## Ops Skill: Scaffold a Promotion Decision Record

### Purpose

Create a new promotion decision record with a consistent naming scheme and required sections, so promotions remain auditable.

### Output location

- `docs/experiments/autonomous_research/records/<YYYYMMDD>_<slug>.md`

### Steps

1. Pick a short `<slug>` describing the promotion topic.
2. Scaffold a new record:
   - `python scripts/scaffold_promotion_record.py --slug "<slug>"`
4. Fill in at least:
   - decision (Promote/Revise/Reject)
   - run directory under `out/`
   - artifacts and gates referenced
5. If promoting:
   - implement the skill changes
   - update registries
   - run `python scripts/check_repo_contract.py`

### Verification

- Record exists under `docs/experiments/autonomous_research/records/`
- Evidence paths are concrete (no placeholders) before claiming Promote

