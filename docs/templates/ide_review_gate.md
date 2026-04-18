# IDE review gate (`project/outputs/review_gate.md`)

Copy this skeleton into **`project/outputs/review_gate.md`** before **`DONE`** or before claiming **Sharpe / CPCV acceptance / portfolio** results.

**Accountability:** The user is **not** expected to audit `project/src/` for you. This file is **your** self-attestation that outcomes and evidence are trustworthy — not a request for someone else to review code. Same **idea as scheme phase**: `review_scheme_package` judges the artifact package — here **`review_gate.md`** judges evidence and **session completion**. **`SUBTASKS.md` all `[x]` is not sufficient**; this file records an explicit **verdict**.

---

## Session completion (review)

**Verdict:** `pass` | `must_fix` — may the session end (**`DONE`**) given **`artifacts/`**, **`project/src/`**, and **`project/outputs/`**?

| Check | Status | Notes |
|-------|--------|--------|
| Numbered **SUBTASKS** lines match **actual** outputs (files exist, metrics/commands align) | | |
| Mandate / scheme gaps reconciled or waived `[!]` | | |
| Open risks or false “complete” flags called out | | |

*(The verdict at the top of this section is **not** implied by SUBTASKS checkboxes alone.)*

---

## Evidence verdict (metrics / CPCV / portfolio)

**Verdict:** `pass` | `must_fix`

**Session / outputs:** (e.g. `outputs/run_meta.json`, paths to JSON/CSV used for metrics)

---

## R-line (must pass or explicit `[!]` waiver in SUBTASKS)

| Check | Status | Evidence (file:line or artifact path) |
|-------|--------|----------------------------------------|
| Portfolio / PnL / Sharpe use a **defined** time series of **portfolio** returns (weights × **realized forward** return per scheme/EDA) | | |
| **Tradable return column** (e.g. **ChangePCT**) matches **`artifacts/`** and EDA — **not** the training **label** in place of PnL unless scheme proves equivalence | | |
| **No lookahead** — features, splits, imputers/scalers align with **`quant_soul`** / mandate | | |
| **Honest names** — reported metrics match the actual computation | | |

---

## H-line (must reconcile or document)

| Check | Status | Notes |
|-------|--------|-------|
| Baseline / CatBoost (or scheme-appropriate baseline) before heavy CPCV grids | | |
| Train/val/test vs acceptance CPCV protocol | | |
| Cost / combinatorics sane vs `SUBTASKS` / `run_meta.json` | | |

---

## Design & alternatives (self-critique)

Fill **before** calling the session complete. This is **your** check — not a human reminder list.

- **Hot path:** Which files/lines dominate cost (training loops, CPCV × labels, etc.)?
- **Alternatives considered:** Name at least one cheaper or more methodology-aligned option you could have used (e.g. joint multi-target fit, smaller `N,k` smoke before full CPCV). Either you **adopted** it, **deferred** with `must_fix`, or **justify** the current design here.
- **Residual risk:** Known slowness or theoretical gap remaining — or `none`.

---

## Must-fix list (if `must_fix`)

- (bullet per issue; link to fix or PR)

---

## Sign-off

- **Accountability:** **execution agent** (primary — you certify this deliverable; no human review assumed)
- **Optional human review:** only if the project explicitly schedules one — not a default obligation
- **Date:** YYYY-MM-DD
