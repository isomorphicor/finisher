## Soul (Values & Non‑Negotiables)

`SOUL.md` captures the project’s values and hard constraints. It answers: what matters most, and what is never allowed?

### Priorities

- **Evidence-first**: a “conclusion” without a verification path is not a conclusion. **Numeric pass/fail cutoffs** belong in execution artifacts once calibrated (or come from an explicit mandate); **scheme-phase** documents define metrics, baselines, and decision *procedure*—not template numbers (`docs/policies/quant_soul.md` §5).
- **Reproducibility**: any critical artifact must be rerunnable and auditable (inputs, config, splits, randomness).
- **No self-deception**: actively look for failure modes; the Reviewer may reject purely on missing evidence.

### Quant/backtest hard constraints (binding)

- **Quant hard gates**: `docs/policies/quant_soul.md` is the minimum standard for trading/portfolio/forecasting/backtesting work in this project.
- If `docs/policies/quant_soul.md` conflicts with other documents, it wins (unless an explicit override is documented with reasons and evidence).

### Engineering

- **Skill-first**: add capabilities as deterministic `skills/` (or MD skills in `docs/skills/`) instead of expanding core.
- **Small, explicit interfaces**: clear module contracts and I/O; avoid implicit global state and unauditable side effects.

