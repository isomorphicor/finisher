---
name: add-python-skill
type: ops
version: 1.0.0
triggers:
  - add python skill
  - create skill template
  - install skill
applies_to:
  - repo
links:
  - scripts/create_skill_template.py
  - scripts/install_skill.py
  - scripts/list_skills.py
  - skills/registry/manifest.json
  - docs/guides/skill_catalog.md
---

## Ops Skill: Add a new Python Skill (Deterministic Tool)

### Purpose

Add a new deterministic Python skill package, register it, and keep the tool surface auditable.

### Preconditions

- You have Python available for this repo.
- You understand the permission policy in `skill_manifest.json` (`requirements.permissions`).

### Steps

1. **Scaffold a new skill package**
   - `python scripts/create_skill_template.py <skill_id> --output-dir /tmp`
   - Creates `runtime.py` + `skill_manifest.json`

2. **Implement the skill**
   - Edit `runtime.py` and ensure it returns the standard envelope:
     - `status: success|rejected|error`
     - `report` (JSON-serializable)
     - `errors` when relevant

3. **Install into the repo registry**
   - `python scripts/install_skill.py /tmp/<skill_id> --repo-root .`
   - This copies the package into `skills/installed/<skill_id>/` and upserts `skills/registry/manifest.json`.

4. **List and verify**
   - `python scripts/list_skills.py --capability custom.<skill_id>`

5. **Document**
   - Update `docs/guides/skill_catalog.md` if the skill is meant for general use.

### Verification

- `skills/registry/manifest.json` contains the new entry with a stable `id`, `version`, and `entry`.
- The skill can be loaded by the runtime router (if applicable) without import errors.

### Rollback

- Remove `skills/installed/<skill_id>/`
- Remove the corresponding entry from `skills/registry/manifest.json`

