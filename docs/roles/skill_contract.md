# Global Skill Contract

This document defines the contract for **deterministic Python tool skills** (`BaseSkill`): interfaces, artifact fingerprints, and the **Layer 1 / Layer 2** split for datasets so modeling code cannot leak targets into ingestion.

It works together with (do not conflate):

| Mechanism | Role |
|-----------|------|
| **[`docs/skills/manifest.json`](../skills/manifest.json)** — MD policy skills | What **schemes and documentation** must cover: `policy.cio`, `policy.data-scientist`, `policy.quant-researcher`, `policy.quant-dev`, `policy.quant-soul`. Single **CIO-led** thread; these are **contracts**, not separate org-chart agents. |
| **This file** | What **Python tool skills** must implement: Layer 1 vs Layer 2 ownership, IO, and performance rules. |

**Canonical links:** [CIO charter](../policies/cio.md) · [Sector ↔ gates (scheme phase)](../experiments/scheme_phase/blueprint.md) · [module contracts](../contracts/module_contracts.md) · [research standards](../contracts/research_standards.md)

---

## 1. Terminology

- **Tool skill**: a deterministic `BaseSkill` subclass exposed to the LLM as a tool.
- **Component**: a helper used by tool skills; not exposed to the LLM.
- **Artifact**: a persisted output (parquet / npy / json / plot) referenced by path + fingerprint.
- **Layer 1 (ingestion)**: tool skills that turn raw structured sources into **standardized dataset artifacts**, quality reports, and fail-closed gates. Aligns with **`policy.data-scientist`** for what the project promises in docs.
- **Layer 2 (modeling)**: tool skills that consume **only** Layer 1 outputs and produce task-specific data (labels, splits, fitted preprocessors, training-ready tables). Aligns with **`policy.quant-researcher`** for research methodology and acceptance narrative.
- **Quant engineering**: backtest/simulation, venue adapters, signal→order plumbing, ops — **`policy.quant-dev`**; not part of the Layer 1/2 dataset split (different artifact family).

---

## 2. Tool skill interface

Every tool skill **must**:

- implement `get_parameters_schema()` and `execute(**kwargs) -> Dict[str, Any]`
- be deterministic; any randomness requires an explicit `seed` parameter
- be idempotent when `save=true`

---

## 3. Standard return envelope

Every tool skill returns a `dict` with:

- `status`: `success | rejected | error`
- `report`: JSON-serializable structured result (no large arrays)
- `artifacts` (optional): list of `{type, path, fingerprint, summary}`
- `errors` (optional): list of `{code, message, details}`

`rejected` = valid request but failed a contract or quality gate.  
`error` = unexpected failure (bug, missing dependency, IO exception).

---

## 4. Artifact fingerprinting and paths

Any saved artifact **must** include a deterministic fingerprint:

- `fingerprint = sha256(canonical_json(parameters + upstream_artifact_fingerprints))`
- output path **must** include `source_name` (or dataset identifier) and the fingerprint
- if `overwrite=false` and the target exists, the skill **must** reuse it and report reuse

**Canonicalization:** `canonical_json(...)` = stable key order, stable list order, no transient fields (timestamps, local absolute temp paths). File inputs **must** reference upstream artifacts by **fingerprint**, not raw bytes.

---

## 5. Ownership (CIO, Layer 1, Layer 2)

- **CIO** ([`docs/policies/cio.md`](../policies/cio.md)): orchestration soul — mandate, gates, acceptance, no fabricated evidence; fail closed.
- **Layer 1** tool skills: own **ingestion contracts** and reject bad data early (fail closed).
- **Layer 2** tool skills: **must not** ingest or “fix” raw sources; they take Layer 1 artifacts only.

**Runtime posture:** one CIO-led flow; policy skills define stage contracts; Python implements Layer 1/2 where needed.

---

## 6. MD policy skills vs tool layers (reference)

| Stage (docs / schemes) | Policy skill | Typical Python side (this doc) |
|------------------------|--------------|--------------------------------|
| Orchestration | `policy.cio` | Gates and workflow; not a dataset layer |
| Data path, dictionary, QA | `policy.data-scientist` | **Layer 1** tool skills |
| Modeling, hypotheses, quant acceptance | `policy.quant-researcher` + `policy.quant-soul` when quant | **Layer 2** tool skills |
| Backtest/sim, adapters, runbooks | `policy.quant-dev` | Engineering skills (outside Layer 1/2) |

**Schemes** follow the policy skills; **persisted dataset code paths** follow Layer 1 / Layer 2 unless a **documented, narrow exception** applies.

---

## 7. Data objects and naming

- `table_path` / `dataset_path` refer to a standardized table artifact (typically Parquet) produced by **Layer 1** tool skills.
- Unless stated otherwise, a “dataset” is time-indexed and includes `date` and an entity key (e.g. `ticker`) when applicable.

---

## 8. Layer 1 vs Layer 2 (anti-leakage)

Hard boundary: prevents leakage and duplicated cleaning across the stack.

### 8.1 Layer 1 — Ingestion / contract and reliability

- Input: raw structured sources (files / DB).
- Allowed: schema mapping, casting, timezone normalization, sort, dedupe, partition, and **target-independent** rule fixes.
- Output: standardized dataset artifacts, quality/profile reports, explicit quality gates (fail closed).
- **Forbidden:** labels; fitting scalers/encoders on full data for task use; target-driven filtering; task-specific feature engineering.

### 8.2 Layer 2 — Task-specific modeling data

- Input: **only** standardized artifacts from Layer 1.
- Allowed: label generation, train/val/test splits, preprocessors fit on training data, windowing, sampling, augmentation, feature engineering tied to `task_spec` / `split_spec`.
- Output: training-ready artifacts, fitted preprocessors, experiment artifacts bound to those specs.

---

## 9. Ingestion tooling and performance

Implementations should stay safe on large data and avoid unbounded full-table reads.

**Baseline stack** (see `requirements.txt`): Polars (primary for IO/transforms, lazy-first where possible), PyArrow, Pandas only for small/bounded cases or sklearn boundaries.

**Large data:** prefer Parquet datasets (file or partitioned directory); downstream training consumes Parquet or derived streams (e.g. Arrow IPC).

**Rules:**

- Prefer Polars over Pandas for ingestion; Pandas only with bounded `sample_rows` or sklearn-only small pipelines.
- File-reading skills **must** support `sample_rows` and column projection (`columns`).
- Avoid unbounded `.collect()` on lazy frames unless bounded by `limit` / `sample_rows` or an explicit persist path.
- Distributed compute (e.g. Ray) is out of scope for v1 unless added to `requirements.txt` with tests.
- In-memory full loads of huge tables are **not** default; require something like `memory_budget_bytes` and return `rejected` when over budget.
