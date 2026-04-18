---
name: session-project-code
type: ops
version: 2.0.0
triggers:
  - session project
  - ide execution
  - MPS
  - Metal
  - paths
  - CatBoost
  - GPU
  - multi-target
  - multi-label
  - parallel heads
  - MLP
  - TCN
  - epochs
  - autoencoder
  - pretraining
applies_to:
  - ide_execution_agent
  - repo
links:
  - docs/reference/ide_execution_rules.md
  - docs/skills/ops/data-first-execution/SKILL.md
  - docs/templates/execution_report_ide.md
  - docs/templates/knowledge_promotion_checklist.md
  - knowledge/ide_lessons.md
---

## Ops Skill: Session `project/` Code Conventions (IDE execution agent)

### Purpose

**Inverst Agent** owns **skills and runners** in this repository (`core/`, `docs/skills/`, `scripts/`).  
**Experiment code** lives under **`out/<name>/<id>/project/`** — session output, not framework source.

**IDE behavioral rules** (SUBTASKS, EDA order, Override, scheme alignment, features vs HPO, glue style, baseline contract wording) are **not** repeated here — defaults live in **`docs/reference/ide_core_rules.md`** (embedded); extended detail in **`docs/reference/ide_execution_rules.md`**. **Backtest / Sharpe:** extended doc → **Tier R** — portfolio metrics from **realized** return series; **never** **`y_true` × normalized `y_pred`** as Sharpe unless scheme proves `y` is that tradable series.

**This skill** only adds: **repo vs session output**, **paths**, **Apple Silicon / GBDT hardware**, and **verification** items that are not duplicated in `ide_execution_rules.md`.

**Framework maintenance:** improve **`ide_execution_rules.md`** + `ide_agent.py` for behavior; improve **this skill** for path/MPS/CatBoost notes only — **do not** check in edits to a user’s `out/.../project/` as if it were product code.

**Search:** the IDE agent exposes **`workspace_grep`** (regex over repo files, default under `docs/`) — use it to **find** relevant rule/skill passages before `workspace_read`, so each round loads **only** what matches the current subtask.

**Rule tiers:** `docs/reference/ide_execution_rules.md` § **Rule tiers (summary)** — **R** / **H** / **P** as in that table.

### Code style (pointer)

Glue density, vectorization, line-count expectations: **`docs/reference/ide_execution_rules.md`** → **Workflow** + **Style** bullets.

### Paths (mandatory)

- Resolve the session project root from the script file:  
  `PROJECT_ROOT = Path(__file__).resolve().parent.parent` when the script lives in **`project/src/`** (preferred) or `project/scripts/`.
- Derive `PROJECT_DATA = PROJECT_ROOT / "data"`, `MODELS_DIR = PROJECT_ROOT / "models"` from that root — **not** from the current working directory.
- Point **raw vendor/feather inputs** (outside the session) via environment variables, e.g.  
  `INVERST_ALGO_DATA_DIR` or `INVERST_DATA_PROCESSED`, with a documented default only in comments — never assume a single machine path without env override.

### Apple Silicon: MPS / Metal (when the user trains neural models)

- **PyTorch:** after `import torch`, use  
  `device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")`  
  and move model/tensors to `device`.
- **TensorFlow / Keras:** on macOS, GPU acceleration uses **Metal** via Apple’s packages (`tensorflow-macos` + `tensorflow-metal`). After importing TensorFlow, list devices with `tf.config.list_physical_devices("GPU")` and enable `set_memory_growth` on GPU devices when present. Tell the user to install the plugin if training is CPU-only.
- **LightGBM / XGBoost:** standard pip builds on Mac usually **do not** use MPS; use **multi-threaded CPU** (`num_threads` / OpenMP) unless the user has a GPU-enabled build. Do not claim MPS for GBDT without evidence.

### Supervised neural nets / GBDT (pointers)

- **Epochs / iterations / multi-target:** **`docs/reference/quant_tech_stack.md`** (*Supervised deep learning*, *GBDT*, *Multiple labels*).
- **IDE** does not duplicate those tables here.

### Agent workflow reminders

- For session-specific pitfalls, **`workspace_read`** **`knowledge/ide_lessons.md`** before repeating mistakes; promote via **`docs/templates/knowledge_promotion_checklist.md`**.
- **Before** generating grids, nested CV, or CPCV `combinations`: **`docs/reference/ide_execution_rules.md`** → **Combinatorics & training cost** — **write down C(N,k)**; default **N=6, k=4** → **15** unless scheme says otherwise.
- **Long training:** same doc → *Time and compute budget* — estimate cost, **stop** bad runs, **pivot** (shrink splits / smoke) instead of waiting.
- If a run needs more tool rounds, raise **`--max-rounds`** or split with **`--task`**.

### Do not do

- **Do not** paste **hardcoded repo-root paths** like `out/<project>/<session>/project/data` as the only way to load files.
- **Do not** keep the **primary** Python package only under `project/outputs/` — library code belongs in **`project/src/`**.

### Verification

- [ ] `Path(__file__)`-relative root + env for external data.  
- [ ] Neural scripts select MPS/Metal when applicable; document pip deps if missing.  
- [ ] **`execution_report.md`** follows **`docs/templates/execution_report_ide.md`**.  
- [ ] Behavioral rules: verify **`docs/reference/ide_execution_rules.md`** when changing IDE policy — not this file for SUBTASKS/Override/EDA order.
