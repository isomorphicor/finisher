## Development Contract (Single Source of Truth)

This document is the **one governing contract** for how this repository evolves.
Its purpose is to prevent “repo drift” (mixed docs, duplicated policies, ad-hoc skills) while keeping the core small and auditable.

### Core principles (NanoClaw-inspired)

- **Small core**: keep orchestration/runtime minimal; add capabilities as skills.
- **Skills over features**: if something can live as a skill (code or markdown), it should.
- **Docs are a system**: every document has a clear type, location, and lifecycle.
- **Fail-closed evidence**: if you cannot measure it, it does not ship (see `docs/contracts/research_standards.md`).
  - Keep contracts minimal and aligned to the runnable workflow; move non-binding guidance to reference.
- **Prompt economy**: runtime system and user prompts stay **short**; canonical detail belongs in `docs/` and skills. Long prompts burn tokens on API models as well as local models and dilute instruction-following.

---

## 1) Repository taxonomy (where things go)

### 1.1 Code

- **Core runtime/orchestration**: `core/`, `runtime/`, `main.py`
  - Must stay minimal, stable, and auditable.
- **Executable skills (deterministic tools)**: `skills/`
  - Callable entrypoints registered in `skills/registry/manifest.json`.
- **Scripts / CLI entry**: `scripts/`
  - Prefer small wrappers around core modules and skills.

### 1.1.1 Code governance (anti-bloat)

This section is binding. It defines where code is allowed to grow and how we keep it iteratable.

**Directory responsibilities**

- `core/`: orchestration + contracts + pure utilities used by entrypoints. No domain “business logic”.
- `runtime/`: tool runtime adapters + intent routing. Keep surface area small; no research logic here.
- `skills/`: deterministic tool skills (file/terminal/workspace ops, data transforms, etc.). Prefer adding capability here over expanding `core/`.
- `scripts/`: thin CLIs only. No large logic; scripts should import from `core/` or `skills/`.
- `tests/`: regression tests for the runnable path.

**Where new code may be added (default)**

- New deterministic capability → `skills/` (+ register in `skills/registry/manifest.json`).
- New orchestration step (only when unavoidable) → `core/` (must stay small; justify why it cannot be a skill).
- New CLI entrypoint → `scripts/` (must be a thin wrapper).

**Forbidden patterns**

- New “one-off” modules in repo root (e.g. `foo.py`): not allowed.
- Duplicated runners / experimental loops under `scripts/`: not allowed; archive or delete.
- Long, multi-hundred-line scripts that embed business logic: move logic into `core/`/`skills/` and keep scripts thin.
- Over-defensive code for hypothetical inputs: not allowed by default. Trust declared contracts (e.g., “Parquet”) and add checks only when required by a real failure mode or an expanded contract.
- Performance regression by default: avoid slow paths (Python loops over rows, eager full-table reads) unless the dataset is explicitly bounded or it is a verified bottleneck workaround.
- Compatibility code without evidence: if a task declares a concrete input contract (format/schema), implement to that contract. Only add compatibility branches when backed by a real failure case and record it.

**Deprecation and deletion policy**

- If a code path is not used by the primary workflow (scheme agent / execution prep / tool routing) and has no tests, it should be deleted or moved to `docs/archive/` with a short note.
- Deprecation must include:
  - removing references from indexes/docs
  - ensuring `python scripts/check_repo_contract.py` stays green

### 1.2 Documentation

All documentation lives under `docs/` and must fit one of the categories below.

- **Agent OS contracts (stable)**: `docs/agent/`
  - `AGENTS.md`, `HEARTBEAT.md`, `MEMORY.md`, `SOUL.md`, `USER.md`
- **Policies & standards (long-lived)**: `docs/policies/` and stable contracts in `docs/contracts/`
  - Example: `docs/policies/quant_soul.md` (quant hard gates), `docs/contracts/research_standards.md`
- **Experiments (active specs and protocols)**: `docs/experiments/`
  - Active experiment blueprints, runbooks, and phase-specific documentation
  - When an experiment becomes “accepted and reusable”, promote it into an ops MD skill under `docs/skills/ops/` and keep links back to the experiment evidence/specs
  - Autonomy experiments must follow the “experiment → evidence → promotion” lifecycle (see `docs/experiments/autonomous_research/`)
- **MD Skills (new, NanoClaw-style)**: `docs/skills/`
  - `docs/skills/policy/*/SKILL.md` — policy skills (constraints, gates, prompt injections)
  - `docs/skills/ops/*/SKILL.md` — playbook skills (step-by-step repo transformations)
- **Archive (non-canonical historical notes)**: `docs/archive/`
  - For deprecated or legacy docs that should not shape current behavior
- **Docs index**: `docs/README.md`
  - Must be updated when adding a new top-level doc category or a new stable contract.

### 1.3 Generated artifacts (ephemeral)

- **Session outputs**: `out/`
  - Never treat `out/` as canonical docs. They are *evidence artifacts* tied to a run.
  - Autonomous “projects” created by the agent should live under `out/` (ephemeral by default) to avoid repo bloat.

---

## 2) MD Skills (contract)

MD skills are markdown packages intended to be **machine-usable** and **human-readable**.
They do not necessarily execute code; they are “behavior/spec/playbook modules”.

### 2.1 Required structure

Every MD skill must be a folder containing `SKILL.md` with YAML frontmatter.
Minimum required fields:

- `name` (string)
- `type` (`policy` or `ops`)
- `version` (string, semver)

Recommended fields:

- `triggers` (list of strings): keywords/intents/task-types that activate the skill
- `applies_to` (list): e.g. `scheme_agent`, `execution_prep`, `all`
- `links` (list): canonical docs or related skills (repo-relative paths preferred)

### 2.2 Registry

- The registry file is `docs/skills/manifest.json`.
- Any MD skill intended for automatic loading must be listed in the registry.

---

## 3) Adding new things (rules of engagement)

### 3.1 Adding a new deterministic (Python) skill

- Create a skill package under `skills/core/` (builtin) or `skills/installed/` (installed).
- Register in `skills/registry/manifest.json` with a stable `id` and `entry`.
- If it expands the tool surface (file/terminal/network), document the policy in:
  - `docs/contracts/research_standards.md` (evidence) and/or
  - a `docs/skills/policy/*/SKILL.md` policy skill (enforcement).

### 3.2 Adding a new policy

- Prefer: `docs/skills/policy/<policy_name>/SKILL.md` that links to the canonical doc.
- The canonical doc should live in `docs/policies/` (or remain in `docs/` if already stable and referenced).

### 3.3 Adding a new ops/playbook

- Add `docs/skills/ops/<playbook_name>/SKILL.md`.
- It must include: prerequisites, step-by-step changes, verification steps, rollback notes.

---

## 4) Enforcement (anti-drift)

The repo provides a lightweight checker script:

- `python scripts/check_repo_contract.py`

It should fail fast when:

- a new `docs/skills/**/SKILL.md` is missing required frontmatter
- new top-level `docs/*.md` files appear without being whitelisted or indexed

---

## 5) Change control (autonomous-safe)

This repo is intended to run in **autonomous mode**. To prevent uncontrolled self-modification, every path belongs to a tier with strict rules.

### 5.1 Tiers

**Tier A — Human-only (do not self-upgrade)**

These documents define the agent’s identity, values, and hard constraints. In autonomous mode, the agent MUST NOT edit them.

- `docs/DEVELOPMENT_CONTRACT.md`
- `docs/agent/*` (Agent OS)
- `docs/policies/*` (e.g. `docs/policies/quant_soul.md`)
- `docs/contracts/*`

Edits to Tier A require explicit human intent (a direct user request) and should be accompanied by a short rationale in `docs/worklog.md`.

**Tier B — Controlled self-upgrade (allowed with evidence)**

These are operational indexes/registries. The agent may edit them autonomously **only when a corresponding change was made and verified**.

- `docs/README.md` (index only)
- `docs/skills/manifest.json` (MD skill registry)
- `skills/registry/manifest.json` (Python skill registry)

Rule: changes must be directly implied by repo changes (new skill added/removed, links updated) and must pass `python scripts/check_repo_contract.py`.

**Tier C — Autonomous logs & records (safe to self-upgrade)**

These exist specifically to be written by the agent.

- `docs/project_status.md` (short, current state)
- `docs/worklog.md` (key behavior changes only)
- `docs/experiments/autonomous_research/records/*.md` (promotion decision records)

### 5.2 Allowed new files (anti-sprawl)

The agent may create new files only in these locations:

- **Experiment specs/notes**: `docs/experiments/**` (must be clearly scoped; promote to skills when accepted)
- **Promotion decision records**: `docs/experiments/autonomous_research/records/<YYYYMMDD>_<slug>.md`
- **MD skills**: `docs/skills/policy/<name>/SKILL.md` or `docs/skills/ops/<name>/SKILL.md` (and register in `docs/skills/manifest.json`)
- **Python skills**: `skills/installed/<skill_id>/...` (and register in `skills/registry/manifest.json`)

Anything else requires explicit human intent.

### 5.3 Deletion/archival rules

- If a doc/script/tool is not on the current runnable path, prefer **delete** or move to `docs/archive/` (non-canonical).
- When deleting a referenced file, update indexes (`docs/README.md`, root `README.md`) and run the contract checker.
