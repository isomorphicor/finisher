---
name: information-collection
type: ops
version: 1.0.0
triggers:
  - literature
  - paper search
  - semantic scholar
  - arxiv
  - related work
  - information retrieval
applies_to:
  - scheme_agent
  - ide_execution_agent
  - repo
links:
  - core/paper_search.py
  - docs/guides/skill_catalog.md
  - docs/skills/ops/research-orchestration/SKILL.md
---

## Ops Skill: Information collection (literature-first)

### Purpose

Define how the agent **gathers external knowledge** to ground research conclusions — starting with **academic literature** already implemented in-repo. This skill is the **extension anchor** for future sources (curated web, vendor APIs); do not assume browser automation exists until wired.

### Implementation (today)

| Component | Role |
|-----------|------|
| [`core/paper_search.py`](../../../core/paper_search.py) | Semantic Scholar + arXiv search; `search_papers` / `search_papers_multi_source`; `format_papers_for_prompt`. |
| [`skills/scheme_phase.py`](../../../skills/scheme_phase.py) | Tool **`paper_search`** for the scheme-phase agent. |
| [`core/scheme_package_io.py`](../../../core/scheme_package_io.py) | Optional **`_presearch_literature`** before scheme refinement. |

See [`docs/guides/skill_catalog.md`](../../../guides/skill_catalog.md) (`paper_search`).

### Contract

1. **Use when** the mandate benefits from prior art — not for filler citations.
2. **Citations** — summarize ideas; **do not** hallucinate titles/venues; paste tool output faithfully into artifacts when used as evidence.
3. **Network** — respect Semantic Scholar / arXiv rate limits; avoid tight loops of repeated identical queries.
4. **Outputs** — literature blocks belong in scheme **`artifacts/`** (or session notes) and should **chain** to conclusions in [`templates/research_report.md`](../../../templates/research_report.md) (Related work / limitations).

### IDE / exploration sessions

Scheme phase has native `paper_search`. IDE sessions **may** gain a thin read-only wrapper over the same backend in a later change; until then, run literature search **via scheme** or **terminal** if explicitly allowlisted for a script that calls `core/paper_search`.

### Verification

- [ ] Queries tied to a falsifiable question ([`research-orchestration`](../research-orchestration/SKILL.md)).
- [ ] Sources recorded where claims depend on them.

### Rollback

N/A — retrieval-only; drop blocks that do not support the mandate.
