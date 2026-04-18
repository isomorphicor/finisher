# Autonomous Research Loop — Experiment Blueprint

**Purpose:** turn this repository into a self-iterating agent by running repeatable autonomy experiments where **accepted behaviors are promoted into skills** (MD skills or Python skills).

This is not a “big framework rewrite”. It’s a disciplined loop that keeps the core small and moves capability into skills.

---

## Core idea: Experiment → Evidence → Promotion

1. **Define a hypothesis** about autonomy (what capability improves, what failure mode is reduced).
2. **Run a bounded experiment** (time/compute/round limits).
3. **Collect evidence artifacts** under `out/` (session + artifacts).
4. **Decide** (promote / revise / reject).
5. If promoted, capture the result as a **skill**:
   - **Ops MD skill** (playbook) under `docs/skills/ops/…` for repo transformations and workflows.
   - **Policy MD skill** under `docs/skills/policy/…` for constraints/gates/prompt injections.
   - **Python skill** under `skills/` when deterministic execution is required.

---

## Experiment structure (v1)

### Inputs

- **Target capability**: e.g. “more reliable scheme artifacts”, “better time-safety compliance”, “fewer hallucinated citations”.
- **Trigger surface**: which tasks should activate it (keywords, intents, task types).
- **Budget**: max rounds, max wall time, max number of reviewer cycles.

### Outputs (required evidence)

For a promotion decision, record at minimum:

- **Run config**: model(s), flags, budgets (already produced by scheme agent runs)
- **Artifacts**: the outputs being judged (e.g. scheme package)
- **Gate results**: any deterministic/LLM reviewer gates used
- **Decision record**: promote/reject + why + what changes were made

---

## Promotion bar (when an experiment becomes a skill)

Promote an experiment into a reusable skill only if:

- **Reproducible**: can be rerun with the same inputs/budget and produce comparable structure (not necessarily identical text).
- **Auditable**: has clear artifacts + gates + decision criteria.
- **Scoped**: doesn’t require expanding core code without strong justification.
- **Safety-preserving**: does not weaken existing hard gates (e.g. `docs/policies/quant_soul.md`).

---

## Where things live

- Active experiment specs: `docs/experiments/autonomous_research/`
- Promoted playbooks: `docs/skills/ops/`
- Promoted constraints/gates: `docs/skills/policy/`
- Deterministic execution: `skills/` (Python)

