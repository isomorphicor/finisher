# Smoke experiment: plan (scheme) + code (IDE)

**Purpose:** Verify in one run that (1) **scheme phase** can produce the four `artifacts/*.md` contracts, and (2) **IDE phase** can write code under `project/`. Use this after LLM/backend configuration changes or before larger research runs.

**Prerequisites**

- Python **3.10+** (repo uses modern typing; macOS `/usr/bin/python3` is often 3.9). The smoke script picks the first 3.10+ interpreter among conda, `~/.local/bin/python3.11`, and `PATH`. Override with **`PYTHON=/path/to/python3`**.
- Working LLM endpoint for scheme + IDE (`config/settings.yaml` or env; see README).
- Run from **repository root** (`PYTHONPATH` implicit when executing `scripts/` from root).

**Hypothesis**

- `run_research_session.py` completes scheme → prep → IDE with exit code **0** when rounds and task are sufficient.

**Procedure**

1. Use a **runs root inside the repo** so `prepare_execution_workspace` can place `project/` under `--workspace-root` (required). The bundled script defaults to **`out/`** at the repo root (same as typical local runs; gitignored). To use `/tmp`, you must pass a matching `--workspace-root` or set `execution_prep` `output_subdir` — see `core/execution_prep.py`.
2. Run the bundled script (recommended) **or** the manual command block.
3. **Success criteria** (all must hold):
   - Process exits **0**.
   - Under `<runs_root>/smoke_plan_code/main/artifacts/`: `research_plan.md`, `derivation.md`, `architecture_draft.md`, `experiment_design.md` exist.
   - **Code:** the IDE may create `project/src/smoke_hello.py` **relative to `--workspace-root`** (often the repo root), i.e. `<repo>/project/src/smoke_hello.py`, not only under `out/.../project/`. Confirm `print("smoke_ok")` appears (or run `python project/src/smoke_hello.py` if the file is minimal).

**Cleanup (after the run)**

- Remove the session tree: `rm -rf out/smoke_plan_code` (safe; under gitignored `out/`).
- If the IDE wrote extra files under `<repo>/project/src/` (smoke prompt uses `project/src/...`), delete or revert them before committing, e.g. `git checkout -- project/src/` or remove only `smoke_hello.py` and any stray smoke outputs.

**Bundled script**

```bash
./scripts/smoke_research_session.sh
```

**Manual one-liner** (must keep sessions under workspace root)

```bash
export INVERST_SCHEME_PHASE_RUNS="$PWD/out"
mkdir -p "$INVERST_SCHEME_PHASE_RUNS"
python scripts/run_research_session.py \
  --project smoke_plan_code \
  --session main \
  --scheme-max-rounds 45 \
  --ide-max-rounds 35 \
  --workspace-root . \
  "$(cat scripts/smoke_research_session_task.txt)"
```

The full prompt text is also in [`scripts/smoke_research_session_task.txt`](../../scripts/smoke_research_session_task.txt) if you copy-paste manually.

**Failure triage**

| Symptom | Action |
|---------|--------|
| `scheme_artifacts_missing` | Raise `--scheme-max-rounds`; shorten task; check LLM timeouts. |
| Scheme `rejected` / `error` | Relax wording; ensure API quota/model available. |
| IDE not `success` | Raise `--ide-max-rounds`; check `project/outputs/` logs and `run_meta.json`. |
| `execution_prep` → `E_SESSION_PATH` | Set `INVERST_SCHEME_PHASE_RUNS` to a directory **inside** `--workspace-root` (e.g. `$REPO/out`), not `/tmp/...` alone with `--workspace-root $REPO`. |
| Import / syntax errors in `core/llm.py` | Use Python 3.10+ |

**Non-goals**

- This is **not** a statistical evaluation of alpha; it is a **pipeline smoke test** only.

**Related**

- [`docs/skills/ARCHITECTURE.md`](../skills/ARCHITECTURE.md) — entrypoints and skill layers.
- [`core/research_session_pipeline.py`](../../core/research_session_pipeline.py) — shared scheme → prep → IDE implementation.
