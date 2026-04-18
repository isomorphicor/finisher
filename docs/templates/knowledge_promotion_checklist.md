# Knowledge promotion checklist (session → `knowledge/`)

Use after a meaningful **`execution_report.md`** (or end of an IDE execution run). Goal: move **durable** insight into the global store without polluting it.

## 1. Decide: promote or not?

| Question | If **no** → skip promotion |
|----------|---------------------------|
| Would this help **another** project/session without the same raw data? | |
| Is it **more** than “we ran script X and it finished”? | |
| Can you state a **lesson** in one paragraph that is **wrong if** … (falsifiable)? | |
| Does it **not** duplicate `quant_tech_stack` / skills verbatim? (If it’s the same, update the repo doc instead.) | |

## 2. Choose a sink (one primary)

| Sink | When |
|------|------|
| **`knowledge/ide_lessons.md`** | IDE/session coding habits, training pitfalls, env/hardware notes, **project-specific** stable exceptions to baseline. |
| **`knowledge/decision_log.jsonl`** | Usually via **`scripts/run_scheme_agent.py`** scoring—scheme-level decisions; not every IDE tweak. |
| **`knowledge/evidence_index.json`** | Cross-cutting **evidence ids** that multiple lessons or decisions reference. |
| **`knowledge/failure_patterns.md` + tag in decision log** | Recurring bad pattern name; use existing tags or propose a new one with rationale. |
| **Repo docs** (`docs/reference/quant_tech_stack.md`, skills) | If the lesson should become **everyone’s default**—open a normal doc change. |

## 3. Minimal promotion path (IDE-heavy runs)

1. Copy the **Lesson** + **evidence path** from `execution_report.md` §4–5.
2. Append to **`knowledge/ide_lessons.md`** using the template at the bottom of that file.
3. If the finding is evidence-heavy, add a short **`items[]`** entry in **`knowledge/evidence_index.json`** (new `evidence_id`, paths, one-line summary).
4. If the run was scheme-scored and deserves a **structured decision**, use the existing **`run_scheme_agent.py`** → `decision_log.jsonl` flow (separate from IDE markdown).

## 4. Anti-patterns

- Logging **every** run → noise; require a **promotion gate** (metric, repeatability, or explicit human “stable”).
- Contradicting **`quant_soul`** in `ide_lessons`—Soul stays in policy docs; lessons may say “we couldn’t meet X because …”.
- Letting `ide_lessons` grow unbounded—**archive or supersede** old entries when defaults change.

## 5. Agent behavior (recommended)

- Before large IDE edits, **`workspace_read`** `knowledge/ide_lessons.md` when the task touches training/code paths already discussed there.
- After a successful baseline + clear delta, **propose** a new `ide_lessons` entry in **`execution_report.md`** §5 (promotion candidates) for human merge—or append if policy allows.
