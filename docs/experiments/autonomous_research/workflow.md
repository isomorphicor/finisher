# Autonomous Research Loop — Workflow

This workflow defines how we run autonomy experiments and keep the repo from drifting.

```mermaid
flowchart TD
    DefineHypothesis[Define hypothesis + triggers + budget] --> RunExperiment[Run bounded experiment]
    RunExperiment --> CollectEvidence[Collect evidence artifacts under out/]
    CollectEvidence --> ReviewEvidence[Review against promotion bar]
    ReviewEvidence --> Decision{Promote?}
    Decision -->|Yes| PromoteSkill[Create/Update skill (MD or Python)]
    Decision -->|No| ReviseOrReject[Revise experiment or reject]
    PromoteSkill --> Enforce[Update registry + run contract checker]
    Enforce --> Done([Done])
    ReviseOrReject --> Done
```

---

## Step 1: Define the experiment

Write a short experiment spec (a new md file under this folder) with: **Hypothesis**, **Triggers**, **Budget**, **Pass/Fail**, **Expected artifacts**.

---

## Step 2: Run the experiment (bounded)

Prefer running the core entrypoint and collecting outputs in `out/`:

- `python scripts/run_scheme_agent.py --model <MODEL> --lang en "<task>"`

---

## Step 3: Evidence and decision

Create a promotion decision record using:

- Template: `docs/experiments/autonomous_research/templates/promotion_decision_record.md`
- Store under: `docs/experiments/autonomous_research/records/`

---

## Step 4: Promotion mechanics

### Promote to an MD skill when:

- the behavior is largely “instructions + checks + workflow” (not deterministic computation)

### Promote to a Python skill when:

- the behavior must be deterministic, executable, and testable via tool calls

---

## Step 5: Enforce anti-drift

Always run:

- `python scripts/check_repo_contract.py`

If promotion adds a new MD skill:

- register it in `docs/skills/manifest.json`

