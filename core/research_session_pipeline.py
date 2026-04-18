"""Shared implementation: scheme phase → optional execution prep → IDE execution agent.

Used by ``scripts/run_scheme_then_ide.py`` and ``scripts/run_research_session.py``.
This module does **not** implement the deprecated ``run_autonomy_loop`` orchestration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.execution_agent import run_ide_execution_agent
from core.execution_prep import prepare_execution_workspace
from core.scheme_contract import REQUIRED_SCHEME_ARTIFACTS
from core.scheme_paths import (
    REPO_ROOT,
    ensure_scheme_session_dir,
    resolve_workspace_root_cli_arg,
    resolve_workspace_root_for_scheme_session,
)

# Default IDE instruction for exploration phase when --explore-task is omitted (EDA / probes only).
DEFAULT_IDE_EXPLORE_TASK = (
    "EDA / probe pass: load inputs from the **paths in the mandate context above** (often absolute paths **outside** "
    "`<session>/project/`). Use `terminal_run` with Python/pandas/pyarrow to inspect files — do **not** assume data was "
    "copied into `project/data/` or skip EDA because nothing is under `project/` except outputs. "
    "Record dtypes, row counts, date span, keys, missingness; if columns suggest returns/PnL/fees/labels, summarize "
    "definitions (no backtest claims yet). Write `project/outputs/eda_report.md`. "
    "Do not claim CPCV, path-multiplicity Sharpe, or production readiness."
)


# Prepended to the scheme-phase user task when Phase 0 exploration succeeded (so the scheme agent reads EDA before artifacts).
SCHEME_TASK_AFTER_EDA_PREFIX = (
    "[Host — Phase 0 EDA finished. **You must** use `read_file` on `project/outputs/eda_report.md` early "
    "(and `list_files` with subdir=project if needed). Ground `research_plan.md` / `experiment_design.md` in that report "
    "(schema, date span, label/return definitions); do not ignore on-disk EDA.]\n\n"
)


def _compose_explore_phase_task(*, scheme_task: str, explore_override: str) -> str:
    """Phase 0 (--eda-first): prepend positional scheme task so EDA sees data paths before artifacts exist."""
    core = (explore_override or "").strip() or DEFAULT_IDE_EXPLORE_TASK
    st = (scheme_task or "").strip()
    if not st:
        return core
    return (
        "## Mandate context (use for **data paths** and constraints — exploration only; scheme artifacts not locked yet)\n\n"
        f"{st}\n\n---\n\n## Exploration instructions\n\n{core}"
    )

# Appended to final IDE --ide-task when --full-experiment-report is set (encourages return/risk write-up).
FULL_EXPERIMENT_REPORT_HINT = (
    "**Reporting (mandatory for this run):** Include **return / PnL analysis** (and vs a simple baseline if applicable), "
    "**risk** (drawdown, volatility, or policy-appropriate metrics), **costs/turnover** if relevant, and **limitations**. "
    "Update `project/outputs/review_gate.md` (or `REVIEW_GATE.md`) and any experiment summary under `project/outputs/`."
)
from core.scheme_agent import (
    get_default_scheme_project_name,
    get_scheme_phase_default_agent_model,
    run_scheme_agent,
    warn_if_implicit_default_project_with_session,
)


def missing_scheme_artifacts(session_dir: Path) -> list[str]:
    adir = session_dir / "artifacts"
    return [n for n in REQUIRED_SCHEME_ARTIFACTS if not (adir / n).is_file()]


def add_scheme_prep_ide_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("task", nargs="*", help="User request for the scheme phase")
    p.add_argument(
        "--project",
        default=get_default_scheme_project_name(),
        help="Top-level folder: <runs_root>/<project>/ (not the session name). Default: env INVERST_DEFAULT_SCHEME_PROJECT or 'default'",
    )
    p.add_argument(
        "--session",
        default="",
        help="Session segment: …/<project>/<session>/; omit → main (or INVERST_DEFAULT_SCHEME_SESSION=timestamp)",
    )
    p.add_argument("--resume-latest", action="store_true", help="Continue latest session under --project")
    p.add_argument(
        "--workspace-root",
        default="",
        metavar="PATH",
        help="Workspace root for prep/IDE tools. Default: empty → from config (paths.workspace_root "
        "or parent of paths.runs_dir; see core.scheme_paths.resolve_default_workspace_root). "
        "If the scheme session is outside the requested root, the pipeline may expand to a common "
        "ancestor of the repo and session.",
    )
    p.add_argument("--lang", choices=("en", "zh"), default="en", help="Scheme artifact language")
    p.add_argument("--allow-ideate", action="store_true", help="If task is empty, let the scheme agent ideate")
    p.add_argument("--scheme-max-rounds", type=int, default=30, help="Max tool rounds for scheme phase")
    p.add_argument("--scheme-model", default="", help="Scheme LLM (default: config / INVERST_SCHEME_AGENT_MODEL)")
    p.add_argument("--ide-max-rounds", type=int, default=120, help="Max LLM+tool rounds for IDE phase")
    p.add_argument("--ide-model", default="", help="IDE coder LLM (default: ide_execution.coder_model / env)")
    p.add_argument(
        "--ide-task",
        default="",
        help="Instruction for the **final** IDE phase (after scheme + prep). Same as run_ide_execution_agent --task. "
        "Not used for the exploration phase; use --explore-task when using --eda-first.",
    )
    p.add_argument(
        "--explore-task",
        default="",
        help="Extra instruction for **exploration IDE only** (Phase 0). The positional scheme **task** is always "
        "prepended so EDA sees data paths before artifacts exist. If omitted, default EDA text is used after that block.",
    )
    p.add_argument(
        "--ide-supplement",
        action="store_true",
        help="Treat --ide-task as supplementary only (same as run_ide_execution_agent --supplement). Requires --ide-task.",
    )
    p.add_argument(
        "--ide-iteration",
        action="store_true",
        help="IDE phase: iteration mode — inject prompts so stale SUBTASKS/DONE do not end the run; require a verifiable "
        "delta (see run_ide_execution_agent --iteration). Env: INVERST_IDE_ITERATION=1.",
    )
    p.add_argument(
        "--explore-before-scheme",
        "--eda-first",
        action="store_true",
        dest="explore_before_scheme",
        help="Run exploration-mode IDE **before** scheme (Phase 0). Creates <project>/<session>/ if needed. "
        "Uses --explore-task or a default EDA probe (not --ide-task). Abort if exploration does not finish with success.",
    )
    p.add_argument(
        "--skip-execution-prep",
        action="store_true",
        help="Skip prepare_execution_workspace (IDE reads artifacts directly from the session).",
    )
    p.add_argument(
        "--execution-output-subdir",
        default="",
        help="If prep runs: legacy subdir under workspace-root; empty = <session>/project/execution_prep/ (set INVERST_EXECUTION_PREP_TIMESTAMP=1 for <ts>/ subfolder)",
    )
    p.add_argument(
        "--abort-ide-on-scheme-partial",
        action="store_true",
        help="Do not run IDE unless scheme status is exactly 'success' (default: run IDE if scheme did not reject/error).",
    )
    p.add_argument(
        "--full-experiment-report",
        action="store_true",
        dest="full_experiment_report",
        help="Append a standard hint to the **final** IDE task: return/risk vs baseline, costs, limitations, review gate "
        "(use with --ide-task or alone for a reporting-focused closeout).",
    )
    p.add_argument("-q", "--quiet", action="store_true", help="Less console output from child agents")


def run_scheme_prep_ide_pipeline(args: argparse.Namespace, *, log_prefix: str = "[research_session]") -> tuple[dict[str, Any], int]:
    """Run scheme → prep → IDE. Returns (result dict, exit code).

    ``log_prefix`` prefixes phase lines (e.g. ``[scheme_then_ide]`` for the legacy CLI name).
    """
    verbose = not args.quiet
    if verbose:
        warn_if_implicit_default_project_with_session(
            project_name=args.project,
            session_name=(args.session.strip() or None),
            stream=sys.stderr,
        )
    task = " ".join(args.task).strip()
    if not task and not args.allow_ideate:
        raise ValueError("Provide a task string or --allow-ideate")

    if args.ide_supplement and not (args.ide_task or "").strip():
        raise ValueError("--ide-supplement requires non-empty --ide-task")

    requested_wr = resolve_workspace_root_cli_arg(getattr(args, "workspace_root", None))
    scheme_model = (args.scheme_model or "").strip() or get_scheme_phase_default_agent_model()

    explore_first = bool(getattr(args, "explore_before_scheme", False))
    pre_session: Path | None = None
    ide_exploration_result: dict[str, Any] | None = None
    if explore_first:
        pre_session = ensure_scheme_session_dir(
            project_name=args.project,
            session_name=(args.session.strip() or None),
            resume_latest=bool(args.resume_latest),
        )
        wr_explore, wr_note_explore = resolve_workspace_root_for_scheme_session(
            scheme_session_dir=pre_session,
            requested_workspace_root=requested_wr,
            repo_root=REPO_ROOT,
        )
        if wr_note_explore and verbose:
            print(f"{log_prefix} {wr_note_explore}", file=sys.stderr, flush=True)
        explore_task = _compose_explore_phase_task(
            scheme_task=task,
            explore_override=(getattr(args, "explore_task", None) or "").strip(),
        )
        if verbose:
            print(f"{log_prefix} Phase 0: exploration IDE (before scheme)…", flush=True)
        ide_explore = run_ide_execution_agent(
            task=explore_task,
            task_mode="supplement" if args.ide_supplement else "override",
            scheme_session_dir=pre_session,
            workspace_root=wr_explore,
            model=(args.ide_model or "").strip() or None,
            max_rounds=int(args.ide_max_rounds),
            verbose=verbose,
            iteration_mode=None,
            exploration_mode=True,
        )
        ide_exploration_result = ide_explore
        if ide_explore.get("status") not in ("success",):
            return {
                "ide_exploration": ide_explore,
                "ide_skipped_reason": "exploration IDE did not complete successfully (--explore-before-scheme)",
            }, 1

    scheme_user_task = task
    if ide_exploration_result is not None and ide_exploration_result.get("status") == "success":
        scheme_user_task = SCHEME_TASK_AFTER_EDA_PREFIX + task

    if verbose:
        print(f"{log_prefix} Phase 1: scheme agent…", flush=True)
    scheme_result = run_scheme_agent(
        task=scheme_user_task,
        model=scheme_model,
        output_lang=args.lang,
        design_lang="en",
        run_root=pre_session if explore_first else None,
        project_name=args.project,
        session_name=(args.session.strip() or None),
        resume_latest=bool(args.resume_latest),
        max_rounds=int(args.scheme_max_rounds),
        allow_ideate=bool(args.allow_ideate),
        verbose=verbose,
    )

    run_root_s = scheme_result.get("run_root") or ""
    st = str(scheme_result.get("status") or "")
    out: dict[str, Any] = {"scheme": scheme_result}
    if ide_exploration_result is not None:
        out["ide_exploration"] = ide_exploration_result

    if st in ("rejected", "error"):
        return out, 1

    if args.abort_ide_on_scheme_partial and st != "success":
        out["ide_skipped_reason"] = f"scheme status is {st!r}, not success (--abort-ide-on-scheme-partial)"
        return out, 1

    session_dir = Path(run_root_s).resolve()
    wr, wr_note = resolve_workspace_root_for_scheme_session(
        scheme_session_dir=session_dir,
        requested_workspace_root=requested_wr,
        repo_root=REPO_ROOT,
    )
    if wr_note and verbose:
        print(f"{log_prefix} {wr_note}", file=sys.stderr, flush=True)
    out["workspace_root_requested"] = str(requested_wr)
    out["workspace_root_effective"] = str(wr)
    if wr_note:
        out["workspace_root_resolution_note"] = wr_note

    missing_art = missing_scheme_artifacts(session_dir)
    if missing_art:
        out["scheme_artifacts_missing"] = missing_art
        out["scheme_session_dir"] = str(session_dir)
        out["ide_skipped_reason"] = (
            "IDE needs all four files under artifacts/: "
            + ", ".join(missing_art)
            + ". The session folder exists, but the scheme phase did not finish writing them "
            "(hit --scheme-max-rounds, LLM stopped early, or a gate failed). "
            "Re-run with a higher --scheme-max-rounds, fix the task, or continue the same session with run_scheme_agent."
        )
        return out, 1

    if not args.skip_execution_prep:
        if verbose:
            print(f"{log_prefix} Phase 2: execution prep…", flush=True)
        osd = (args.execution_output_subdir or "").strip() or None
        prep_result = prepare_execution_workspace(
            scheme_session_dir=session_dir,
            workspace_root=wr,
            output_subdir=osd,
        )
        out["execution_prep"] = prep_result
        if prep_result.get("status") != "success" and verbose:
            print(json.dumps(prep_result, ensure_ascii=False), flush=True)

    if verbose:
        print(f"{log_prefix} Phase 3: IDE execution agent…", flush=True)
    final_ide_task = (args.ide_task or "").strip()
    if getattr(args, "full_experiment_report", False):
        hint = FULL_EXPERIMENT_REPORT_HINT.strip()
        final_ide_task = f"{final_ide_task}\n\n{hint}".strip() if final_ide_task else hint
    ide_result = run_ide_execution_agent(
        task=final_ide_task,
        task_mode="supplement" if args.ide_supplement else "override",
        scheme_session_dir=session_dir,
        workspace_root=wr,
        model=(args.ide_model or "").strip() or None,
        max_rounds=int(args.ide_max_rounds),
        verbose=verbose,
        iteration_mode=(True if getattr(args, "ide_iteration", False) else None),
    )
    out["ide"] = ide_result

    ide_st = ide_result.get("status")
    if ide_st not in ("success",):
        return out, 1
    return out, 0
