# Promotion Decision Records

This folder stores **promotion decision records**: concise, auditable writeups explaining why an experiment result was (or was not) promoted into a stable skill.

## Naming convention

- `<YYYYMMDD>_<slug>.md`
  - Example: `20260325_md-skill-registry-hardening.md`

## Required content

Use the template:

- `docs/experiments/autonomous_research/templates/promotion_decision_record.md`

At minimum, each record must include:

- the hypothesis and bounded experiment design (budget)
- the run directory under `out/` (evidence location)
- the decision (Promote / Revise / Reject) and rationale
- the promotion plan (paths + registries) if promoted

## Lifecycle

- If **Promote**, create/update the target skill and register it (MD registry or Python registry), then run `python scripts/check_repo_contract.py`.
- If **Revise**, keep the record and add a follow-up record once the revision is rerun.
- If **Reject**, keep the record to prevent re-litigating the same idea without new evidence.

