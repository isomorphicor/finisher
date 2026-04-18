---
name: add-md-skill
type: ops
version: 1.0.0
triggers:
  - add md skill
  - add policy skill
  - add ops skill
applies_to:
  - repo
links:
  - docs/skills/manifest.json
  - docs/DEVELOPMENT_CONTRACT.md
---

## Ops Skill: Add a new MD Skill (Policy/Ops)

### Purpose

Add a new Markdown-based skill under `docs/skills/` in a way that is:

- discoverable (registered in `docs/skills/manifest.json`)
- machine-usable (valid YAML frontmatter)
- governance-compliant (passes `python scripts/check_repo_contract.py`)

### Preconditions

- You are editing this repository directly.
- You are **not** adding executable Python code here; this is Markdown-only.

### Steps

1. **Pick the type**
   - `policy`: constraints, gates, prompt injections (must link to canonical policy docs when applicable)
   - `ops`: repo transformation playbooks (must include verification + rollback)

2. **Create the folder + SKILL.md**
   - Policy: `docs/skills/policy/<skill-slug>/SKILL.md`
   - Ops: `docs/skills/ops/<skill-slug>/SKILL.md`

3. **Add required YAML frontmatter**
   - Required keys: `name`, `type`, `version`
   - Recommended: `triggers`, `applies_to`, `links`

4. **Write the body**
   - Policy: include purpose, applicability, enforcement semantics, and required evidence.
   - Ops: include preconditions, explicit steps, verification, and rollback.

5. **Register the skill**
   - Edit `docs/skills/manifest.json` and append an entry:
     - `id`: `policy.<name>` or `ops.<name>` (stable)
     - `type`, `version`, `path` (must point to the `SKILL.md`)
     - `triggers`, `applies_to`, `links`

6. **Verify**
   - Run: `python scripts/check_repo_contract.py`
   - Fix any registry or frontmatter failures before proceeding.

### Notes

- Keep the core small: if the change can live as an MD skill, do not add it to `core/`.
- If this MD skill introduces a new stable doc, link it in `docs/README.md`.

