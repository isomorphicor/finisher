## Agents (Project Contract)

This repo is **research-first** and **CIO-led**. `AGENTS.md` defines only what is needed to keep work executable, reviewable, and auditable.

**Organizing idea:** match **single-operator** research—one accountable chain spans data, modeling, evaluation, and delivery without org-chart walls. The **CIO** is the **thinking / orchestration** role (typically a **CIO agent** that schedules workers; **human** may remain ultimate authority or co-pilot). **Methodology and tooling** live in policies, reference, and `knowledge/`; they are not departmental silos.

**Unified model (normative):** **CIO orchestration** + **execution agents** (scheme, IDE coder, …) + **MD policy skills as contracts** + **sectors as artifact/gate layers**—spelled out in `docs/policies/cio.md` (including **event-driven** handoff: each execution milestone **invokes CIO** for audit / next directive). **Stage names** (data / research / engineering) refer to **deliverables and which gate failed**, not to parallel org units.

### Roles (default)

- **CIO (thinking / orchestration agent, project soul)**: sets mandate and acceptance, **dispatches** execution agents, **reviews** at milestones (see `docs/policies/cio.md` **Event-driven handoff**), signs off. May be **fully automated** (CIO agent ↔ workers), **human-led**, or hybrid.
- **Execution agents** (e.g. scheme-phase writer, IDE execution loop): implement tasks under CIO direction; **completion** should **hand back** to CIO for the next instruction (product intent — runtime wiring may be script/meta-loop or host events).

### Optional labels (not boundaries)

- The following are **optional shorthand** for prompts or audits. They are **not** mandatory seats or handoffs between “departments.”
  - **Layer 1 (ingestion)**: time-safe datasets and contracts; reject bad data early — aligns with `policy.data-scientist` and **Layer 1** in [`docs/roles/skill_contract.md`](../roles/skill_contract.md) §8.
  - **Layer 2 (modeling)**: hypotheses, experiment design, reproducible evidence — aligns with `policy.quant-researcher` and **Layer 2** in [`docs/roles/skill_contract.md`](../roles/skill_contract.md) §8.
  - **Reviewer**: apply gates; reject on missing evidence.
- **Mapping to MD policy skills** (same contracts, discoverable in `docs/skills/manifest.json`):
  - Data-oriented work → `policy.data-scientist` (`docs/skills/policy/data-scientist/SKILL.md`).
  - Modeling / acceptance / quant methodology → `policy.quant-researcher` + `policy.quant-soul` as needed (`docs/skills/policy/quant-researcher/SKILL.md`, `docs/skills/policy/quant-soul/SKILL.md`).
  - Backtest/simulation/adapters/execution plumbing → `policy.quant-dev` (`docs/skills/policy/quant-dev/SKILL.md`).
  - Orchestration soul → `policy.cio` (`docs/skills/policy/cio/SKILL.md`).
- **Stage-only vs closed-loop:** research topics may be **one link in a chain** (no full tradable output in the same deliverable) unless the mandate is investment-closed-loop—see `policy.quant-researcher` and `docs/policies/quant_soul.md`.
- Skip them whenever a single CIO thread is clearer.
- If the user provides **no concrete topic**, CIO may **ideate a bounded quant research topic** and proceed autonomously.
  - The ideated topic must be recorded as an artifact (e.g. `artifacts/ideated_task.json`) for auditability.

### Required outputs (scheme phase)

- `research_plan.md`
- `derivation.md`
- `architecture_draft.md`
- `experiment_design.md`

See `docs/experiments/scheme_phase/` for the current runnable workflow.

### Non-negotiables

- **CIO charter (orchestration soul)**: `docs/policies/cio.md`
- **Quant hard gates** (executable rigor for quant schemes): `docs/policies/quant_soul.md`
- **Evidence-first**: predefine pass/fail *logic* (what to compare, vs which baselines, time-safe protocol) before running experiments; **lock numeric thresholds** only after data/mandate calibration or in execution artifacts, not as generic tables in the scheme package (`docs/policies/quant_soul.md` §5).
- **Reproducibility**: inputs/config/splits/seeds must be traceable.

### Extensibility

- Add capabilities as deterministic skills (`skills/`) or MD skills (`docs/skills/`) with registry/contract checks.
- **Registry:** `docs/skills/manifest.json`. **Sector ↔ gates ↔ scheme phase** table: `docs/experiments/scheme_phase/blueprint.md` (“Sector stages ↔ minimal artifacts ↔ gates”).
- **Execution tooling config** (`config/agents.yaml`) selects **models** for optional scheme-phase hires (e.g. reviewer); it does **not** replace the policy-skill contracts above for what “data / research / dev” mean.

