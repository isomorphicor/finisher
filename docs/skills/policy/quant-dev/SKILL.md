---
name: quant-dev
type: policy
version: 1.0.1
triggers:
  - quant dev
  - backtest engine
  - simulation
  - broker API
  - OMS
  - execution adapter
  - signal to order
  - runbook
  - paper trading
applies_to:
  - scheme_agent
links:
  - docs/policies/quant_soul.md
  - docs/policies/cio.md
  - docs/roles/skill_contract.md
---

## Policy Skill: Quant Dev (engineering near production)

### Purpose

Define the **capability surface** for **quant engineering** near production—aligned with common industry Quant Dev scope, trimmed for this repo: **production-like backtest and simulation**, **broker / exchange / OMS / desk / FIX / vendor API adapters** (paper, sim, test; not live desk as default), **signal→order plumbing** (risk checks, state, audit logs), and **non-research ops** (scheduling, monitoring, recon, runbooks, deploy). Turn **Quant Researcher outputs** into **runnable software**: **full tradable specs** when the mandate is closed-loop; otherwise **stage outputs and integration points** (APIs, schemas, replay hooks).

**This repo does not** treat **live production trading** (real-money order entry / desk operation) as a **default** focus—errors are costly; emphasize **testable, regressible** systems first.

Orchestration stays **CIO**; this skill is **not** a separate “trader” agent.

### Canonical policy / cross-links

- **`docs/policies/quant_soul.md`** — acceptance path; engineering implements **OOS/path replay** compatibly with Soul, but **does not** replace research-side protocol design.
- **`docs/policies/cio.md`** — single-owner thread.
- **`docs/roles/skill_contract.md`** — boundaries vs research/data artifacts.

### Main responsibilities

1. **Backtest & simulation (priority)**: engines/simulators with **production-like** constraints: costs, slippage, capacity, halts/suspensions, partial fills, multi-asset/account constraints; **OOS/path replay** compatible with **`quant_soul` acceptance path** (implementation supports research definitions).
2. **Trading / venue APIs (adapters)**: brokers, exchanges, OMS, desks, FIX, vendor APIs as project chooses; ship **testable adapters** and **config/secrets** handling; default stance **connect + drill + paper/sim**, not **production desk operation** as this repo’s headline.
3. **Signal → order plumbing** (when execution is in scope): map QR outputs—**target weights/positions** in closed-loop tasks, or **agreed intermediate representations** in stage-only work—into **order intents / parameters** (risk limits, slicing, time windows) via **pipelines and state machines**; **pre-trade checks** and **audit logs**.
4. **Non-research quant engineering**: scheduling, monitoring, deploy/rollback, feature flags, **recon/attribution pipes** (with data/research), performance/reliability; docs and **runbooks**.
5. **Boundaries**: **does not** own label design, acceptance protocol, or statistical conclusions (QR); **does not** own raw **data dictionary / ETL** (DS); **owns** operational correctness, testability, traceability, and **version alignment** with research artifacts.

### Typical deliverables

Runnable backtest/simulation notes, adapter/API notes, **signal→order** spec, monitoring/recon highlights, explicit **sim vs live** gaps (latency, matching simplifications).

### Boundaries

- **Does not** define research hypotheses or **`quant_soul` acceptance rules** (QR / policy).
- **Owns** execution-side correctness, testability, traceability; **live trading** if ever in scope needs **extra process and risk controls** and is **not** this repo’s default focus.
