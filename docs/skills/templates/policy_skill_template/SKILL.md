---
name: example-policy
type: policy
version: 0.1.0
triggers:
  - example
applies_to:
  - all
links: []
---

## Policy Skill: Example

### Purpose

State the non-negotiable constraints this policy enforces and what it protects against.

### When it applies

- List the triggers in plain language (task types, keywords, intents).

### Enforcement semantics

- **Prompt injection**: what text must be shown to the agent
- **Gates/checklists**: what must be present in artifacts; what is a blocking failure
- **Fallback**: what to do if evidence is missing

### Required evidence (minimum)

- List required artifacts or checklist items.

