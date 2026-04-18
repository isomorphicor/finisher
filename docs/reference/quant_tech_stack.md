# Quant Tech Stack (Reference, Not a Constraint)

**IDE coding defaults** live in **`docs/reference/ide_core_rules.md`** — read that first for sessions; this file is **model/training detail**, not a doc you must traverse before writing code.

Practical defaults for models and tooling. You may deviate **after** documenting why— but **skipping** the baseline habits below is how most weak finance-ML projects fail; they then wrongly conclude “ML doesn’t work here.” **Tree + neural training discipline** is the ladder to a **stable baseline**; “clever” training without that baseline is usually noise.

---

## Exploration Policy (Prior, Not Prison)

- Use priors to cut search waste; update them when new evidence wins under fair evaluation.
- Reversibility: say when you pivot, stop, or roll back; budget a few anti-prior probes; log dead ends so you do not repeat them.

---

## Default Baselines

*Subsections below are the **baseline recipe** (general quant ML). IDE defaults: **`docs/reference/ide_core_rules.md`** (minimal); full tiers/workflow: **`docs/reference/ide_execution_rules.md`**. Not Soul hard gates, but **do not treat them as optional** until you have a working baseline run.*

### Tabular prior (classification & regression)

- **Strong prior:** Gradient-boosted **trees** (CatBoost-style) are the **default best-in-class** for **tabular** classification and regression in this workflow — you do not skip them for panel/alpha work. Training is **simple:** default hyperparameters often work well; **~300 rounds**, **no early stopping** as the silent default, other params **default** is an acceptable **first** baseline (`ide_core_rules.md` still requires your **CatBoost** runs for evidence — see **§ C**). **Where the work goes:** **feature engineering** and data alignment, not endless HPO on trees before features are solid.
- **Daily bar + features ready:** On **day-frequency** panel data, **CatBoost** training — including typical **acceptance** CPCV (e.g. modest N×k) — is often **~10–20 minutes** wall-clock on CPU-class hardware: **very high ROI** vs jumping to heavy per-label loops or large NNs. **Use it as the first serious model** once `X` is in place; portfolio Sharpe outcomes remain **mandate- and data-dependent** (strong results are possible when labels and costs are aligned — not a universal promise).
- **Ensembles:** A **multi-model** stack (e.g. blend or stacking of several diverse models) **may** beat a **single** tree baseline — try **after** a strong tree baseline; document weights / fold / OOS protocol. **Retention:** if model **A** is **worse** than the tree baseline **alone**, but **A + trees** (ensemble) **beats** the baseline, **A** can **remain** as a component — log the ensemble (`ide_core_rules.md` **§ C**).

### GBDT: fixed iterations

- **Default:** Fixed `iterations` / `num_boost_round` (~**300** typical, **200–500** common). Same budget across candidates unless the scheme opts out. **Baseline habit:** **300 rounds**, **defaults elsewhere**, **no early stopping** for the first serious CatBoost run unless the scheme requires ES — then iterate on **features**, not knobs.
- **Avoid:** Validation-only early stopping as the silent default (one val split → noisy `best_iteration`).
- **If early stopping:** Say why; fix seeds/splits; do not report only `best_iteration`.
- **Log:** Fixed round count or your early-stop rule.

### Supervised deep learning: epochs & baselines

- **Scope:** The **~1 epoch** habit applies to **supervised prediction** (fit to labels: MLP, TCN, Transformer on **y**). It does **not** apply to unsupervised pretraining, generative training, or RL—those use their own budgets (often many epochs or steps) and often **early stopping**; see sections below.
- **Epochs:** Default exploration **~1 epoch** for supervised nets. More epochs often hurt on noisy alpha; large epoch counts need a reason.
- **Baselines:** Strong **MLP** on features. **IDE:** NN training-efficiency reference = **feedforward MLP, ≤6 hidden layers, hidden dim 128** (full IDE wording: **`ide_execution_rules.md`** / modeling order). At **comparable parameter count**, training must not be **an order of magnitude** slower in wall/throughput/memory than that reference. **Autoencoder / similar pretraining** for **downstream** use: pretrain once, multi-head downstream when inputs are shared—the **pretrain phase** itself follows the Representation rules, not the 1-epoch supervised rule.
- **Log:** Model family + epoch count (or step-equivalent).

### Unsupervised / self-supervised pretraining (separate from supervised 1-epoch rule)

- **Epochs:** Set **by task** (often **tens–hundreds**). **Early stopping** on a held-out reconstruction/val proxy is **normal**. Log `max_epochs`, patience, and stopping rule.
- Do not confuse this stage with the **supervised** baseline contract for IDE runs (`docs/reference/ide_execution_rules.md`).

### Generative / world models (training budget)

- **Epochs:** **Case-by-case**; often many epochs with **early stopping** or step budgets. Document architecture, loss, and stopping.

### RL (training budget)

- **Episodes / epochs / updates:** **Not** the supervised 1-epoch rule—use what the environment and algorithm need; **early stopping** on rollout metrics is common. See **RL / Control** for algorithm preferences (e.g. GRPO-style stability).

### Multiple labels / multi-target

- **When:** Joint training only if targets are **compatible** (regime, scale, gradients—not arbitrary bundles).
- **IDE:** **Tabular/panel default**; sequence/text/image + big pretrain is out of default one-shot scope. **Regression/classification** — **CatBoost** quality baseline. **Multi-*y*** — **first** the **cheap baseline:** simple **label grouping** / **label weights** + **features** → **one** **CatBoost** train; log metrics. **Do not** jump to **CPCV + per-label** before this. Anything heavier must **≥** that baseline (`ide_core_rules.md` **§ C**). **NN** — ref **MLP (≤6 hidden @128)** at **~same params**, not **10×** worse.
- **Neural:** Shared trunk + parallel heads; prefer simpler unless you test a specific bias.

- Time series (planning): simple state-space / linear before heavy sequence nets.
- AutoML (e.g. AutoGluon): good for a fast broad baseline, not assumed to be the ceiling.

### Model Feasibility First (Planning Rule)

- Do not freeze model families before you have seen data.
- At plan time: screen N × D, compute/time budget, stability risk; justify feasibility at target scale.

### Where Real Alpha Work Starts

Beyond commodity baselines: architecture matched to geometry, loss aligned to utility, sampling/regularization/robustness, features/representation, **acceptance** (stability + overfitting risk)—not only one-shot Sharpe.

**IDE execution session** (glue style, SUBTASKS order, features-before-HPO, Override, scheme alignment, backtest scheme-first): defaults in **`docs/reference/ide_core_rules.md`** (embedded); full detail in **`docs/reference/ide_execution_rules.md`** — **not duplicated** here.

---

## Panel / tabular preprocessing (time safety)

- **Default (many quant models):** **no** panel **`ffill`/`bfill`** and **no** global mean/median as the first choice for missing features — use **`fillna(0)`** (or a domain sentinel) and/or **missing-indicator columns** so the model sees “was missing” explicitly. Use **`ffill`** or **train-split-only** imputation only when the scheme or EDA documents why past values or global stats are valid for that feature.
- **`bfill`:** **never** a default — backward fill uses **future** within the series → **lookahead leakage** for supervised features at \(t\).
- **Implementation:** **vectorized** fills (Polars `fill_null` / pandas `fillna` on projected columns), not Python loops over all columns. **At scale:** **Polars** for heavy transforms; **pandas** for small slices or library glue — **`ide_core_rules.md` § B** (not optional polish).

---

## Representation (Unsupervised / Self-Supervised)

- Tabular/market: autoencoder-style MLP encoders; mask/contrastive when labels are weak.
- Training may use full history; **evaluation** stays time-safe.
- **Epoch policy:** Same as **Default Baselines → *Unsupervised / self-supervised pretraining*** (many epochs + early stop OK)—not the supervised **1 epoch** rule.

---

## RL / Control

- **Training length:** Not the supervised **1-epoch** rule—often **many** updates with **early stopping** on rollout/val proxies. See **Default Baselines → *RL (training budget)***.
- Prioritize reward, constraints, environment realism; pick optimizers for non-stationarity + stability.
- Prefer **synthetic** envs for **training** when it improves stability and coverage; **walk-forward** is exploratory only—not primary supervised evidence (`docs/policies/quant_soul.md`). **Supervised** acceptance: default **CPCV**-class path evidence or a **documented** alternative with comparable overfitting scrutiny (see Soul §3).
- **Experience:** **GRPO-style** training (group-relative / comparative policy updates—inspired by GRPO) has been the **stable** approach here; **SAC-class** runs **underperformed** in past tries—do **not** treat SAC/TD3 as the default allocator recipe.
- SAC/TD3 only if actions are truly continuous **and** the sim is credible—and you have a reason to expect them to beat GRPO-style after your environment tests.

### Validation regime (practical)

- Forward validation: optimistic in one-sided regimes—not final supervised evidence.
- Rolling-window supervised: small effective N, unstable—niche exploratory, not default production.
- Hand-built index/futures timing factors (rare): only with explicit caveats + conservative risk.
- **Timing / allocation RL:** **Train** heavily in **synthetic or sim** when helpful; **production** can be justified when **inference / execution on real data** is **stable** under an explicit evaluation plan (real-history OOS, shadow metrics, stress tests)—not “only live months” as the sole gate. Document sim→real gap and monitoring; align with **`docs/policies/quant_soul.md`** §3 **RL / control**.

### Deployment refit after acceptance (optional ops notes)

- **Policy anchor:** After **supervised** acceptance (default: CPCV-class path evidence, or an **equally documented** alternative per Soul §3), refitting a **locked** spec on **all approved history** for serving is **allowed** (`docs/policies/quant_soul.md` §3)—it does not replace the **acceptance** evidence already on record. **Practice varies:** some production lines use only path-based or k-fold deployment artifacts; others may use a single full-history refit—**document** the recipe and monitor live behavior.
- **Neural nets — full retrain churn:** Empirical experience includes **large prediction or PnL behavior shifts** after periodic **full retrains** on growing data. Treat scheduled full retrains as an **operational risk** (shadow traffic, canaries, rollback), not only an offline metric story.
- **Online / incremental learning:** When non-stationarity or retrain instability matters, **online learning** or incremental updates are a **valid research and engineering direction**—**not** a Quant Soul hard gate. If adopted, define leakage-safe updates, drift monitoring, and how evidence still aligns with time-safe evaluation (`docs/policies/quant_soul.md`).

### Pattern: experts → RL allocator (optional)

1. Train supervised experts under an **accepted** protocol (default CPCV-class paths per Soul §3); keep only accepted ones; optional k-fold (or other) **deployment refit** of **locked** specs after acceptance — **no** new tuning on that refit (`docs/policies/quant_soul.md` §3).
2. RL allocator allocates across experts; state can mix expert PnL/risk series + market latents (timestamps aligned; latents need not match stock feature dim).
3. Align end-to-end: expert target → tradable signal → allocator reward. High overfitting at expert or allocator → fail-fast.

### Supervised signal first; RL as allocator

- Direct signals when labels are constrained weights; light post-process (e.g. ReLU + normalize) if constraints hold.
- RL here mainly allocates **across** experts, not necessarily stock-level actions—needs enough experts with stable series.
- **Boundary:** high-dimensional drifting equity universes are poor for direct RL per-stock; low-D or fixed actions (futures timing, low-D allocation) are more realistic.

---

## Generative / World Models

- Objectives that yield usable conditional distributions for planning; define **planner I/O** first (moments, samples, latents).
- Do not jump to heavy sequence models before a simple baseline fails.
- **Epoch policy:** See **Default Baselines → *Generative / world models (training budget)***—not the supervised 1-epoch default.

---

## Anti-Pattern Checklist

- Default LSTM/GRU for any series without a simpler baseline.
- SOTA chasing without inductive bias or constraints.
- Tuning to win one backtest without controlling research DoF.
- Adding temporal modules when tabular + window flattening is already strong.

