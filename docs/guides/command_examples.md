# Command Examples

Minimal commands for the current workflow (two steps).

## One-shot: scheme + IDE (single process)

Runs **`run_scheme_agent`** → **`prepare_execution_workspace`** (unless `--skip-execution-prep`) → **`run_ide_execution_agent`**. Final JSON includes `scheme`, `execution_prep` (if run), and `ide`.

Implementation: [`core/research_session_pipeline.py`](../../core/research_session_pipeline.py). Prefer **`run_research_session.py`** (skill-first name); **`run_scheme_then_ide.py`** is the same pipeline and flags.

```bash
python scripts/run_research_session.py --project algo_alpha --ide-max-rounds 200 \
  "Your scheme-phase research task"
```

Equivalent:

```bash
python scripts/run_scheme_then_ide.py --project algo_alpha --ide-max-rounds 200 \
  "Your scheme-phase research task"
```

Optional IDE-only instruction:

```bash
python scripts/run_research_session.py --project algo_alpha --ide-task "Baseline first" "Scheme task here"
```

Only run IDE if scheme returns exact `success`:

```bash
python scripts/run_research_session.py --project algo_alpha --abort-ide-on-scheme-partial "…"
```

**If you see `scheme_artifacts_missing` or IDE `E_SCHEME`:** the session folder exists but `research_plan.md` / `derivation.md` / `architecture_draft.md` / `experiment_design.md` were not all written (round limit, failure, or early stop). Increase `--scheme-max-rounds`, refine the task, or continue with `run_scheme_agent.py` on the same `--project` / `--session`.

---

## 1) Run scheme

```bash
python scripts/run_scheme_agent.py --project algo_alpha "your research task"
```

## 2) Prepare execution workspace from latest scheme session

```bash
python scripts/run_execution_prep.py --project algo_alpha --resume-latest --workspace-root .
```

## Optional: specify a fixed session

`--session` names the second path segment; it does **not** choose the project. Use **`--project algo_alpha`** (or `export INVERST_DEFAULT_SCHEME_PROJECT=algo_alpha`) **and** `--session v1` to get `<runs_root>/algo_alpha/v1/` (e.g. `out/algo_alpha/v1/` when runs root is `out/`).

```bash
python scripts/run_scheme_agent.py --project algo_alpha --session v1 "your research task"
python scripts/run_execution_prep.py --project algo_alpha --session v1 --workspace-root .
```

## IDE-only on an existing session

```bash
python scripts/run_ide_execution_agent.py out/algo_alpha/v1 --max-rounds 80
```

**`--task`** alone is treated as a full **Override** (mandatory `scheme_alignment_audit.md` + appendix). For focused asks (e.g. “optimize compute”) without that gate, use **`--supplement --task "..."`** — the prompt requires an edit under `project/src/` or `outputs/supplement_blocked.md`.

## Output layout

```text
<runs_root>/<project>/<session_or_ts>/
```
