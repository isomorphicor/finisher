## Memory (Project State)

`MEMORY.md` stores information that remains true across sessions: conventions, baselines, paths, non-negotiables, and decisions proven effective/ineffective.
It is not for one-off logs; short-lived notes should live in session artifacts or `docs/worklog.md` (if present).

### Environment and paths

- **Workspace**: repo root
- **Local data (current stage)**: `docs/experiments/scheme_phase/local_data_stocks.md`
  - features: `/home/foo/test/data/processed/DatasetAShare.ftr` (if still used)
  - Data file paths are environment-specific; do not hardcode absolute paths in repo docs.
### Default policies


- **Quant research hard gates**: `docs/policies/quant_soul.md`
- **Scheme-first**: produce executable design artifacts in the scheme phase before tool execution and coding.

### Known baselines

- **Latest accepted scheme (baseline)**: `out/<project>/<session>/` (update when a run is accepted; default project name is often `default`)

### Important decisions

- Only add items that are **not already codified** elsewhere (especially `docs/policies/quant_soul.md`).
