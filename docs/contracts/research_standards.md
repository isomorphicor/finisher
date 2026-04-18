# Research Standards & Evidence Gates

**Version:** 1.1  
**Date:** 2026-03-11  
**Purpose:** define the Definition of Done for research deliverables as evidence artifacts. This document is intentionally contract-oriented: it specifies what must be produced, not how to code it.

Module boundaries and IO contracts: [module_contracts.md](module_contracts.md).  
Dataset schema contracts: keep them minimal and enforce them in code and tests.

## 0) Golden Rule (Fail Closed)

If you cannot measure it, it does not ship.

Reviewer/CIO acceptance must reject when any required evidence artifact is missing or unverifiable.

## 1) Minimum evidence (current workflow)

This repo’s current runnable path is **scheme-first**. Minimum evidence means:

- **Scheme package** exists and is complete (see `docs/contracts/module_contracts.md`)
- Any claim of “works” must be backed by a **rerunnable path** (inputs + protocol + pass/fail) even if execution happens in IDE

When execution artifacts exist, they must be referenced via artifact records (type/path/fingerprint/summary).

## 2) Time Safety (No Look-Ahead)

The system must make time alignment explicit:

- define the “as-of time” for every feature column
- define the label horizon and the earliest timestamp at which it is knowable
- enforce purging/embargo rules when labels overlap feature windows

Minimum checks:

- **feature leakage check**: no feature may use future prices relative to its as-of time
- **label leakage check**: training labels must not bleed into the feature window used for training
- **split leakage check**: no overlapping windows across train/test when windows are used

Minimum executable gates (v1):
- When a task produces labels, predictions, signals, or any windowed features, the delivery MUST include evidence that the three checks above were run and passed.
- Required evidence artifacts (minimum):
  - `split_spec` (time-safe split definition, including purge/embargo rules when applicable)
  - `split_index` (the concrete train/val/test time ranges or indices)
  - `leakage_report` (structured findings + pass/fail + reasons)
- The `leakage_report` MUST be able to answer (without re-running code):
  - what the feature “as-of” rule was
  - what the label horizon / earliest-knowable time was
  - what purge/embargo (or overlap prevention) rules were applied
  - what was checked and what failed (if rejected), with actionable remediation hints

## 3) Data Quality Gates (Inputs)

Data Engineer outputs must include:

- missingness summary per column
- duplicates summary (time/entity duplicates)
- outlier policy and a report of outlier handling
- schema validation result against declared contracts
- time coverage and sampling frequency checks (including gaps)

If the dataset does not satisfy the declared schema or time alignment rules: reject.

## 4) Quant protocol alignment (binding)

For any quant/backtest/forecasting task, this repo binds to:

- `docs/policies/quant_soul.md`

In particular:
- Scheme-phase deliverables define metric families, baselines, and decision procedure; **numeric acceptance cutoffs** are not universal—mark `provisional` until calibrated or mandated (`docs/policies/quant_soul.md` §5).
- **Exploration** (model and HPO): use simple **time-safe** train/validation/test — **do not** use **CPCV** for training or hyperparameter search during model selection (`docs/policies/quant_soul.md` §3).
- **Final acceptance** (after the modeling spec is locked): evidence must use **CPCV (purge+embargo)**; walk-forward is not accepted for supervised model acceptance here.
- CPCV evidence should be path-based rather than a single split report: construct multiple OOS paths from combinatorial splits, run per-path portfolio backtests, and report distributional evidence (for example Sharpe distribution, dispersion, tail outcomes, and overfitting-risk diagnostics such as PBO when model/parameter search breadth is meaningful).
- Modeling target must be objective-aligned with strategy acceptance objective (PnL/risk-adjusted portfolio performance). The mapping from prediction to tradable weights/signals must be explicit and reproducible.
- If overfitting-risk diagnostics breach threshold (for example PBO above configured threshold), candidate status must be **rejected** and further tuning on the same candidate line must stop (fail-fast).
- Portfolio backtest/reporting remains required as a downstream step after model acceptance (still time-safe and leakage-free).
- After CPCV acceptance, deployment inference weights **may** be trained under the **same locked spec** using a **different** time-safe scheme (e.g. k-fold), path exports from CPCV, or a **full-history refit** on approved data — **without** new hyperparameter or architecture tuning on that deployment run. **Material spec changes** require a **new** CPCV cycle (`docs/policies/quant_soul.md` §3).

## 5) Backtesting Standards (Third-Party First)

Backtests are executed using third-party libraries by default. A bespoke engine is not required for v1 and must be justified if introduced.

Required backtest evidence:

- explicit time alignment rules and data requirements
- deterministic run configuration (seed, library version, spec fingerprints)
- complete cost assumptions (fees, slippage, borrow, corporate actions policy if relevant)

## 6) Reporting Standard

Every research delivery must include:

- what was tested (scope and hypotheses)
- what data was used (sources, time range, universe)
- what protocol was used (split/CV, purge/embargo)
- what results were obtained (tables, key metrics)
- what limitations remain (explicit)

