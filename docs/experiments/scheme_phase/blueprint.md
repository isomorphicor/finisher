# Scheme Phase Workflow — Experiment Blueprint

**Version:** 2026-03-15 · Executable outline.

**Scope:** Open-ended research (direction + detail both open). Current implementation focuses on producing a scheme package (design artifacts) and leaves execution to the IDE.

**Experiment:** The scheme agent produces a scheme package from a given fuzzy idea (or ideates one when empty).  
**Run command (primary):** `python scripts/run_scheme_agent.py --lang en "fuzzy idea"` — a self-directed agent that writes the scheme package via deterministic tool skills (`paper_search`, `read_file`, `write_file`). **Default LLM** is `config/agents.yaml` → `scheme_phase.default_agent_model` (override with `--model` or env `INVERST_SCHEME_AGENT_MODEL`).
- More examples and args: see `python scripts/run_scheme_agent.py --help`.
- **Workflow reference:** [workflow.md](workflow.md).

---

## Input / Output

| Input | Output (scheme package) |
|-------|-------------------------|
| Fuzzy idea / conceptual / one-sentence goal (e.g. "discover anomaly patterns in unlabeled time series", "improve recall and interpretability of a detector") | research_plan (with literature_synthesis), derivation, architecture_draft, experiment_design, data/training/eval; delivered after S7 self-check + S8 review (and revision loop) |

**Language:** For local large models, English reasoning is typically much faster. The scheme workflow translates non-English inputs (including human feedback in revision) into English for internal reasoning, then writes artifacts in the requested output language (`--lang`) unless `--no-translate-output` is set.

**Traceability:** Theory assumptions ↔ candidate architectures ↔ experiment variables must be mappable.

**Autonomous scheme agent artifacts (selected):**
- `artifacts/session_meta.json`: session metadata (id, created_at, status).
- `artifacts/run_config.json`: run config (models, flags, max_rounds).
- `artifacts/refined_task.json`: structured "single source of truth" task spec (fuzzy need → refined task).
- `artifacts/ideated_task.json`: when the user provides no task, the CIO records the ideated task text.
- `artifacts/structure_gate.json`: deterministic structure gate (required section headings per artifact).
- `artifacts/topic_anchor_gate.json`: deterministic keyword-anchor gate result (refined key_terms vs scheme text).
- `artifacts/quant_soul_gate.json`: deterministic quant gate (time-safety, leakage/bias, costs/constraints, metrics, failure modes) when quant-related.
- `artifacts/topic_alignment.json`: LLM topic-alignment gate result (blocking issues + must_fix).
- Optional: `artifacts/scheme_summary.json` (machine-readable summary; enable via CLI flag).
  - `schema_version`: `scheme_summary_v1`
  - Contains structured `hypotheses`, `variables`, `metrics`, `experiments`, and `data_protocol` for downstream execution planning.
  - When enabled with `--emit-experiment-matrix`, also writes `artifacts/experiment_matrix.json` (`schema_version`: `experiment_matrix_v1`) derived deterministically from scheme_summary.
- Optional (human review loop): `artifacts/response_to_review.md` + `artifacts/revision_request.json` + `artifacts/revision_gate.json` when `--revision` is used to revise an existing session.

**Collaboration:** The scheme workflow is **under CIO**. The current implementation is single-run (no parallel design/aggregation in this repo).

---

## Minimum Artifact Requirements

- **Consistency with `quant_soul` (acceptance wording):** Success criteria and pass conditions must describe **what** is measured and **how** decisions compare to baselines and mandate. Do **not** treat scheme-phase tables of generic numeric targets (Sharpe, turnover, drawdown) as fixed; use `provisional` / TBD until calibrated or mandated—see `docs/policies/quant_soul.md` §5.
- **research_plan:** Background, problem, success criteria, **literature_synthesis** (mainstream/frontier/gaps), references.
- **derivation:** Notation, assumptions, derivation steps and justification.
- **architecture_draft:** ≥2 candidate architectures and comparison; ≥1 non-mainstream or targeting frontier/gaps.
- **experiment_design:** Assumptions, variables, matrix, metrics, pass conditions, execution order.
- **Data/training/eval:** Data split and time-safety, training strategy, evaluation protocol (can be in experiment_design).
- **Protocol staging (required):**
  - Separate **exploration protocol** (fast iteration) from **acceptance protocol** (final CPCV path-based evidence).
  - For CPCV/time splits in planning, use `provisional` parameters with determination logic; lock concrete numeric values only after data exploration and record them in execution artifacts.

---

## Sector stages ↔ minimal artifacts ↔ gates (aligned with CIO + policy skills)

**Purpose:** Map **stage lenses** (data / research / engineering) to **what must exist**, **which gate fires**, and **which MD policy skill** documents the contract. Sectors are **artifact layers**, not org-chart seats; the CIO thread remains single-owner—see `docs/policies/cio.md` (“Unified operating model”).

| Stage lens | Minimal artifacts (typical) | Gates / checks in this workflow | Policy skill (`docs/skills/manifest.json`) | Scheme-phase touchpoints |
|------------|----------------------------|----------------------------------|--------------------------------------------|--------------------------|
| **CIO orchestration** | Refined task / mandate, full scheme package, review outcome | `artifacts/structure_gate.json`, `artifacts/topic_anchor_gate.json`, `artifacts/topic_alignment.json`, S7 self-check + S8 review | `policy.cio` | Session flow, `refined_task.json`, `ideated_task.json` when empty input; final sign-off |
| **Data** | Data dictionary (post-processing), data contract, QA/EDA notes, lineage, version identity | Contract + QA completeness (fail closed on bad data in execution paths; scheme must state provenance assumptions) | `policy.data-scientist` | `experiment_design` / data protocol sections; assumptions feeding derivation |
| **Quant research** | Hypothesis, labels/protocol, acceptance evidence, reproducibility, `quant_soul` self-check when applicable | `artifacts/quant_soul_gate.json` when **quant-related**; methodology must satisfy `docs/policies/quant_soul.md` | `policy.quant-researcher`, `policy.quant-soul` | `research_plan`, `derivation`, `experiment_design`, `architecture_draft`; quant sections in scheme text |
| **Quant dev (engineering)** | Backtest/sim design, adapter/signal→order specs, runbooks, sim-vs-live gaps | No separate JSON gate in scheme-only phase; engineering validation applies when building runners/adapters | `policy.quant-dev` | `architecture_draft` execution / systems notes; post–scheme-phase implementation |

**Quant research nuance:** A scheme may be **stage-only** (e.g. new label, feature representation, algorithm) without delivering full **tradable portfolio weights** in the same package. **Investment-closed-loop** mandates require **tradable artifacts + `quant_soul` acceptance** as in `policy.quant-researcher`. `quant_soul_gate.json` applies when the work is **quant-related** per runner logic.

**Skill routing note:** `config/agents.yaml` still lists **hired** reviewer/translator models for scheme-phase automation; **capability** semantics (what “data vs research vs dev” means) are defined by the **policy skills** above, not by extra agent personas. Prefer **`docs/skills/manifest.json`** as the registry when adding or routing MD policy skills.

---

## Experiment Script (entry and args)

See original runner notes in the repository scripts (entrypoints under `scripts/`). This blueprint is the canonical *workflow contract* for scheme-phase experimentation.
