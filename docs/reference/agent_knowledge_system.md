# Agent Knowledge System (Global, Cross-Project)

This project keeps long-term agent knowledge in a compact global store under `knowledge/`, not in `out/`.

## Why

- `out/` is session/project evidence and can grow quickly.
- Core knowledge should persist across projects and remain concise.
- A compact structure improves iteration speed and reduces drift.

## Files

- `knowledge/theory_snapshot.md`  
  Current formal framework (few pages, math-first, replaceable).
- `knowledge/decision_log.jsonl`  
  Structured key decisions (accepted/rejected/revised) with reasons and evidence ids.
  Include compact decision quality fields:
  - `value_score` (0-10): estimated research value of this iteration
  - `failure_pattern` (nullable string): low-value/failed-direction tag
- `knowledge/evidence_index.json`  
  High-signal index of supporting/contradicting evidence.
- `knowledge/open_questions.md`  
  Small active queue of unresolved questions.
- `knowledge/failure_patterns.md`  
  Stable taxonomy for low-value/failed-direction tags (`failure_pattern`).
- `knowledge/ide_lessons.md`  
  **Promoted** lessons from IDE execution / session `project/` work (see **IDE execution → knowledge promotion** below). Not a mirror of every `execution_report.md`.

---

## IDE execution → knowledge promotion (baseline + learning loop)

**Problem:** Session outputs live under `out/.../<project>/<session>/project/` and can be huge. **Global defaults** for IDE behavior are **`docs/reference/ide_core_rules.md`** (primary); `quant_tech_stack.md` and `ide_execution_rules.md` are optional depth — not a nested reading mandate. **Gaps:** project-specific truths that are **stable** but not yet worth a repo doc change.

**Mechanism (three layers):**

| Layer | Role |
|-------|------|
| **Repo defaults** | `ide_core_rules` (IDE), Soul, `quant_tech_stack`, optional `ide_execution_rules`, skills — **baseline contract**; agents should not assume a full-doc walkthrough. |
| **Session evidence** | `execution_report.md`, metrics, scripts under `out/.../project/` — **raw** run record. |
| **`knowledge/`** | **Promoted** high-signal lessons + structured decisions — **long-lived**, cross-project memory. |

**What to promote from IDE runs**

- A **durable** lesson (hardware, data quirk, confirmed exception to a default) with a **promotion gate** (metric, repeat run, or explicit “stable”).
- A **failure pattern** tag + short note when the same mistake recurs (align with `failure_patterns.md`).

**What *not* to promote**

- One-off noise, “script succeeded”, or text that **duplicates** `quant_tech_stack` — if it should be universal, **edit the repo doc** instead of `ide_lessons.md`.

**Sinks (pick one primary per insight)**

1. **`knowledge/ide_lessons.md`** — append using the template in that file (newest-first sections).
2. **`knowledge/evidence_index.json`** — add an `items[]` entry when an evidence id should be citeable from multiple places.
3. **`knowledge/decision_log.jsonl`** — mainly via **`scripts/run_scheme_agent.py`** scoring for **scheme** iterations; IDE-only runs are **not** auto-appended unless you add a manual JSONL line following the same schema (prefer `ide_lessons` for IDE-heavy narratives).
4. **Repo PR** — if the lesson should become the **new** default for all agents, update `quant_tech_stack` / skills / `ide_agent` as usual.

**Operational checklist:** `docs/templates/knowledge_promotion_checklist.md`.

**“Autonomous learning” caveat:** Writing to `knowledge/` does **not** change model weights; it **grounds** future runs if the agent **reads** these files. Promotion should stay **gated** (repeatability or review); otherwise the store becomes contradictory noise.

## Update policy

- Prefer updating these files over creating many new docs.
- Promote only high-signal findings from project runs (`out/`) into `knowledge/` (see **IDE execution → knowledge promotion** and `docs/templates/knowledge_promotion_checklist.md` for `ide_lessons.md`).
- Keep reversibility explicit: record trigger conditions for replacing old beliefs.
- If new evidence repeatedly dominates old assumptions, revise `theory_snapshot.md`.
- `scripts/run_scheme_agent.py` evaluates each run with a deterministic progress score (0-100) and appends to `knowledge/decision_log.jsonl` only when gates pass: **artifact fingerprint** must not already appear anywhere in the log (avoids duplicate lines when re-running the same session or after trimming the log), **first write for a project** requires **major-update-level** score (≥85), and follow-up writes require fingerprint change plus the same major threshold. Use `--no-log-knowledge` to skip evaluation. **Scheme-only** runs (four markdown artifacts only) are **capped at 60** unless `empirical_anchor` reaches the configured gate (default: 28), which usually requires **`scheme_summary.json` and/or `experiment_matrix.json`** (`--emit-json-summary` / matrix) in addition to text signals—aligned with `docs/policies/quant_soul.md`.
  - Suggested baseline:
    - 40: core artifact completeness
    - 30: material delta vs previous project run
    - 20: quality signals (pass conditions + CPCV/OOS-path evidence)
    - 10: novelty/value signal
  - Default update threshold: score >= 70
  - Major update candidate hint: score >= 85
  - Logged entries also carry `value_score` and optional `failure_pattern` to accumulate "what not to do" knowledge, not only successful paths.
