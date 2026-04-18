---
name: cognitive-research-flow
type: ops
version: 1.0.3
triggers:
  - experiment design
  - probe
  - pilot
  - multi-label
  - cost benefit
  - research strategy
  - HPC
  - parallel training
  - hyperparameter
  - scale out
applies_to:
  - scheme_agent
  - ide_execution_agent
  - repo
links:
  - docs/skills/ops/data-first-execution/SKILL.md
  - docs/policies/quant_soul.md
  - docs/reference/ide_core_rules.md
  - docs/reference/quant_tech_stack.md
---

## Cognitive research flow (capability, not hard policy)

**What this is:** A **problem-solving and sequencing** playbook—how to spend attention, wall time, and compute **deliberately**. It does **not** replace **`docs/policies/quant_soul.md`** or other **enforceable** gates (e.g. validation protocols you must not violate). Those remain **constraints**; this skill is **judgment under those constraints**.

**What this is not:** A license to weaken methodology. If a method is **disallowed** by policy (e.g. a specific validation pattern), that rule wins.

---

### Finite budgets (mental model)

- **Compute is not infinite** — even with many cores or GPUs, every run has a **marginal cost**: electricity, contention, debugging surface, and opportunity cost of what you did *not* try.
- **Calendar time is not infinite** — iteration loops are bounded by meetings, data freezes, and decision deadlines.
- Therefore **every step should pass a lightweight cost–benefit check**: *What question does this run answer? What cheaper experiment could falsify the same hypothesis? What do we learn if it fails?*

---

### Cost–benefit at each step

Before expanding work (more labels, more folds, more models, more hyperparameters), write down:

1. **Hypothesis** — one sentence.
2. **Cheapest falsifier** — smallest run that could prove the idea wrong or not worth scaling.
3. **Expected information** — what decision becomes easier after this run (architecture choice, data fix, stopping).
4. **Blast radius** — lines of code, rows processed, jobs spawned; prefer **small blast radius** until (2) is satisfied.

Reject **unmotivated Cartesian products**: nested loops over targets × folds × configs **without** a prior “probe” that justifies the full grid.

---

### Probe → commit → scale (“以点带面”)

1. **Probe (pilot)** — On **one** label (or a minimal target subset), end-to-end pipeline with **default or light** hyperparameters: tree models often need little tuning; neural nets may only need **fine-tuning** after the architecture is right. Goal: **lock direction** (model family, feature depth, validation harness), not leaderboard score.
2. **Commit** — Explicitly record in `experiment_design` / `SUBTASKS`: which probe outcomes generalize to “all labels” vs which are label-specific.
3. **Scale out** — Reuse the **same** architecture and training recipe across labels (per-target heads or multi-target), **parallelizing** where independent. Do **not** repeat full heavy protocols per label **until** the probe answered the structural question.

This is compatible with **high parallelism**: parallel jobs are for **executing a already-pruned plan**, not for **brute-forcing an unpruned grid**.

---

### No silent omission of mandated steps (budget overruns)

Whatever the scheme, **`artifacts/`**, **SUBTASKS**, **`review_gate`**, or policy names as a **required chain**—**do not drop a link** because it is slow, tedious, or inconvenient. That includes (non-exhaustive): **validation**, **backtest / portfolio return**, **acceptance diagnostics**, **EDA**, **cost model**, **reporting**.

If **wall time or compute exceeds budget**, **fix the plan**, do not erase the step:

- **Shrink** scope (smaller data slice, fewer folds, smaller `N,k`, smoke → full).
- **Engineer** (vectorize, batch, parallelize, cache, cheaper baseline first).
- **Restructure** (e.g. multi-target or shared trunk **after** a probe shows it fits the mandate—see below).
- **Document** any **deferral** in `project/outputs/` (what was reduced, why, what remains)—**silent omission is never OK**.

“Ran out of time” with no written pivot is a **planning / execution failure**, not a neutral shortcut.

---

### Multi-target vs per-label (must be probed, not assumed)

Whether **multi-output / multi-target** is appropriate depends on **label correlation, noise, and mandate**—it is **not** universally faster or better. Treat it as a **probe decision**:

- **Probe:** cheap joint baseline (e.g. grouped or multi-head GBDT) on a **slice** or **one** representative period before committing to full acceptance combinatorics.
- **Commit:** if the probe shows shared structure helps, scale with multi-target or shared trunk + heads; if labels are heterogeneous, per-label or grouped heads may be more honest.

---

### High-performance computing (why it matters)

- **Correct HPC** (vectorized I/O, batched training, multi-process or multi-GPU where safe) **reduces wall time per hypothesis**, so you can afford more probe cycles within the same calendar budget.
- **Naive Python loops** over dates × assets × labels for work that could be **vectorized or batched** waste cycles on the **wrong** experiments—fast wrong answers are still wrong.
- Prefer: **profile hot paths** → fix I/O and tensor layout → **then** scale job count — see **`docs/reference/ide_execution_rules.md`** (pipeline & I/O) and **`docs/reference/quant_tech_stack.md`**.

---

### Relation to other skills

- **`docs/skills/ops/data-first-execution/SKILL.md`** — concrete IDE workflow (probe EDA, then code). This skill sits **above** it: **when** to expand and **how much** to spend before expanding.
- **`docs/policies/quant_soul.md`** — non-negotiable methodology and evidence. **Cost–benefit never overrides policy.**

### Relation to research-orchestration

- **`docs/skills/ops/research-orchestration/SKILL.md`** — chooses **mandate class** (full-stack vs slice) and **phase order** (e.g. EDA before locking scheme). This skill supplies **probe → commit → scale** economics **inside** a chosen phase; orchestration decides **whether** that phase runs and **when** to stop.
- **`docs/skills/ops/manual-supervisor-playbook/SKILL.md`** — when you are not using the all-in-one CLI, use this checklist to pick **which** L2 steps to run (explore-only vs scheme vs IDE, etc.).

---

### Checklist (self-review)

- [ ] Is there a **one-label (or minimal) probe** before a full multi-label sweep?
- [ ] Is the next run the **cheapest** way to answer the current question?
- [ ] Are we **reusing** one architecture across labels after the probe, instead of re-tuning from scratch for each?
- [ ] Are heavy loops **vectorized / batched** where possible before adding more parallel jobs?
- [ ] Does the writeup state **what was deprioritized** and why (opportunity cost is explicit)?
- [ ] **No mandated step omitted silently** — if anything in the agreed chain was cut or shrunk for budget, is it **documented** (and ideally fixed via staging/HPC/re-scope rather than dropped)?
- [ ] If **multi-target** was used or rejected, was there a **probe** (cheap joint vs per-label) rather than a default full grid?
