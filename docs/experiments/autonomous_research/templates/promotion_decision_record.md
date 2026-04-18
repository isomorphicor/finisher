# Promotion Decision Record (Template)

Use this template to decide whether an experiment result should be promoted into a **skill**.

---

## Summary

- **Decision**: Promote | Revise | Reject
- **Capability**: (what improved?)
- **Scope**: (what tasks/triggers does it apply to?)

## Hypothesis

Describe the autonomy hypothesis and why it matters.

## Experiment design (bounded)

- **Budget**: (max rounds / time / review cycles)
- **Runner**: (e.g. `scripts/run_scheme_agent.py`)
- **Models**: (design/review/translator if relevant)

## Evidence

- **Run directory**: `out/...`
- **Key artifacts**:
  - (list paths)
- **Gate results**:
  - (list files, pass/fail)

## Analysis

- What changed vs baseline?
- What failure modes were reduced?
- What new invariant is enforceable?

## Promotion plan (if Promote)

- **Skill type**: MD ops | MD policy | Python tool
- **New/updated paths**:
  - `docs/skills/...` or `skills/...`
- **Registry updates**:
  - `docs/skills/manifest.json` and/or `skills/registry/manifest.json`
- **Docs updates**:
  - `docs/README.md` (if new stable docs)

## Rollback

If promotion is reverted, list what to delete/revert.

## Checklist

- [ ] Evidence is auditable (paths + artifacts exist)
- [ ] Change is scoped (no core bloat)
- [ ] Safety gates preserved (e.g. quant hard gates)
- [ ] `python scripts/check_repo_contract.py` passes

