# Failure Pattern Taxonomy

Purpose: keep low-value/failed-direction tags stable across runs so the agent can accumulate "what not to do" knowledge.

## Core Tags (v1)

- `incomplete_research_package`
  - Missing one or more required scheme artifacts.
  - Usually indicates an execution/coverage issue, not a valid research conclusion.

- `weak_acceptance_definition`
  - Acceptance/pass-condition evidence is weak or ambiguous.
  - Typical symptom: missing explicit pass/fail thresholds or insufficient validation protocol detail.

- `low_novelty_direction`
  - Iteration lacks meaningful hypothesis/model/experiment novelty.
  - Typical symptom: mostly rephrasing prior design without new evidence-bearing changes.

- `low_progress_iteration`
  - Overall progress score below update threshold.
  - Typical symptom: small edits with limited impact on quality or decision value.

- `speculative_without_empirical_anchors`
  - Artifacts exist but `empirical_anchor_35` stays below the gate that unlocks scores above 60 (by default: without `scheme_summary.json` / `experiment_matrix.json`, text-only anchors max out below that gate).
  - Typical symptom: scheme-only markdown before structured outputs or IDE-backed runs; `scripts/run_scheme_agent.py` applies `SCHEME_ONLY_MAX_SCORE` (60) until the gate passes.

- `training_baseline_drift`
  - Session training code **silently** ignores the **baseline training contract** (e.g. supervised NN default epoch budget, GBDT fixed iterations, portable paths) without `experiment_design.md` or documented ablation.
  - Typical symptom: large implicit epoch counts, validation-only early stopping as the only GBDT story, hardcoded `out/projects/...` paths in scripts.

## Usage Notes

- Use one primary tag per logged iteration for deterministic tracking.
- Prefer stable tag ids; add new tags only when recurring failure modes are clearly distinct.
- When adding a new tag, update both this file and the tagging logic in `scripts/run_scheme_agent.py`.
