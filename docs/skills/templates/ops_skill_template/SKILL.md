---
name: example-ops
type: ops
version: 0.1.0
triggers:
  - refactor
applies_to:
  - repo
links: []
---

## Ops Skill: Example Repo Transformation Playbook

### Purpose

Describe the repo transformation goal (what changes, why it’s safe, what it enables).

### Preconditions

- Required tools, permissions, and assumptions.

### Steps (must be explicit)

1. What to change (files/paths).
2. How to validate correctness (commands/tests).
3. How to update docs/contracts after the change.

### Verification

- Exact checks that should pass (commands + expected signals).

### Rollback

- How to revert safely if verification fails.

