# Local Data Scheme Experiment (Stocks)

This document defines the current phase objective:
- Use local stock data to drive the agent to autonomously design a **scheme package**
- If the scheme is executable, proceed to tool calls and coding tests

## 1) Known local data

- Data directory: `/home/foo/test/data/processed`
- Current visible files:
  - `DatasetAShare.ftr` (features main table)
  - `hist_label.ftr` (label main table)

Note: your working convention is “one features, one label”; we map them to the two files above.

## 2) Experiment goal (this round)

In **scheme phase**, the agent should produce high-quality design artifacts first, and **not** write production/business code yet.

Required outputs (scheme package):
- `research_plan.md`
- `derivation.md`
- `architecture_draft.md`
- `experiment_design.md`

Recommended extra outputs (if enabled):
- `scheme_summary.json`
- `experiment_matrix.json`

## 3) Short Prompt (for Scheme Agent)

Use the following prompt directly as input (for `scripts/run_scheme_agent.py` or `main.py --mode scheme_agent`):

```text
Design an implementation-ready stock-research scheme (no production code yet) using:
- features: /home/foo/test/data/processed/DatasetAShare.ftr
- label: /home/foo/test/data/processed/hist_label.ftr

Follow quant_soul as the default policy and focus on executable details.

Task essentials:
- DatasetAShare includes ChangePCT for return calculation.
- hist_label is the target optimal holding weight.
- Convert predictions to weights via L1 or long/short normalization.
- Evaluate portfolio PnL primarily by Sharpe.

Output exactly:
- research_plan.md
- derivation.md
- architecture_draft.md
- experiment_design.md

Non-negotiables:
- Explicit key inference and validation (panel index is time + stock code; infer concrete column names from schema).
- Strict time-safe, leakage-free evaluation.
- At least 2 model candidates, with at least 1 non-mainstream candidate.
- Supervised workflow: use train/validation/test for exploration, then CPCV (purge+embargo) for final strict backtest.
- Walk-forward is prohibited for supervised model acceptance.
- Use baselines for anchoring only; propose frontier or custom architecture when it improves objective-level evidence or iteration efficiency.
- experiment_design must include hypotheses, variables, experiment matrix, pass conditions, and execution order.
- Keep the scheme directly executable in IDE by human+agent.
```

## 4) Run examples

### 4.1 Produce the scheme first (recommended)

```bash
python scripts/run_scheme_agent.py --lang en "PASTE_THE_PROMPT_ABOVE"
```

### 4.2 Latest accepted scheme (current baseline)

For tools experiments, use a scheme session under the canonical layout (see `scripts/run_scheme_agent.py`: default `--project default`):

- `out/<project>/<session_id>/`
- Core artifacts:
  - `out/<project>/<session_id>/artifacts/research_plan.md`
  - `.../derivation.md`
  - `.../architecture_draft.md`
  - `.../experiment_design.md`

(Replace `<project>` and `<session_id>` with your run; e.g. `out/algo_alpha/v3/artifacts/`.)

### 4.3 Generate an IDE execution checklist (using the baseline)

```bash
python scripts/run_execution_prep.py out/<project>/<session_id> --workspace-root .
```

## 5) Pass criteria (before coding)

Proceed to tools/coding only when:
- The 4 core artifacts exist and have complete structure
- `experiment_design.md` includes executable run order and **explicit pass/fail logic** (metrics vs baselines, time-safe protocol); numeric targets may stay `provisional` until data/cost calibration unless the mandate fixes them (`docs/policies/quant_soul.md` §5)
- Time-safe split plan and leakage checks are explicit
- At least 2 candidates are proposed, including at least 1 non-mainstream candidate
- Data alignment/join-key assumptions and validation steps are explicit
- Prediction-to-weight mapping is defined (L1 or long/short normalized) and Sharpe is the primary evaluation metric

## 6) Next step (after passing)

After the scheme passes, proceed to tools experiments (current default baseline: `20260324T164256Z`):
- Goal: call `workspace_*` and `terminal_run_allowlisted`
- Action: generate a minimal runnable code skeleton from `experiment_design` (load data, split, baseline train, evaluation scripts)
- Acceptance: run from IDE with one command and produce output result files

