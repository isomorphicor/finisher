#!/usr/bin/env python3
"""DEPRECATED — do not use for new work.

**Use instead:** ``python scripts/run_research_session.py`` or ``python scripts/run_scheme_then_ide.py``
(same pipeline: scheme → prep → IDE; see ``docs/skills/ARCHITECTURE.md``). This script remains only
for backward compatibility and will be removed in a future release.

---

Autonomy loop: scheme → **package review** (revise until pass) → prep → IDE → optional workflow iteration.

**Phase 1 — Design:** ``run_scheme_agent`` until ``success`` (with internal partial retries). Then
``review_scheme_package``; if ``can_proceed`` is false, ``revise_scheme_session`` with review feedback
and re-review, up to caps — **no IDE until review passes** (unless ``--skip-scheme-review``).

**Phase 2 — Execution:** prep (optional) → built-in IDE or external coder. ``--max-cycles`` retries IDE
only within the same workflow.

**Phase 3 — Iteration (optional):** ``--max-workflow-iterations`` > 1 runs another round after a
**successful** IDE pass: feedback is read from ``project/outputs/execution_report.md`` and
``review_gate.md``, then ``revise_scheme_session`` → review loop → prep → IDE again.

Scheme sessions and generated ``project/`` trees live under
``<scheme-runs-root>/<project>/<session>/`` (e.g.
``…/projects_generated/algo_alpha/main``). Default runs root: ``config/settings.yaml``
``paths.runs_dir`` (unless overridden by ``--runs-root`` or env
``INVERST_SCHEME_PHASE_RUNS``; ``--runs-root`` is applied from argv before ``core`` imports).
Default session folder when ``--session`` is omitted: ``main`` (override with
``INVERST_DEFAULT_SCHEME_SESSION`` or ``timestamp`` for UTC-stamped dirs).

See also: ``docs/README.md``, ``docs/guides/command_examples.md``,
``docs/experiments/scheme_phase/blueprint.md``.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

def _parse_runs_root_from_argv(argv: list[str]) -> Path | None:
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--runs-root" and i + 1 < len(argv):
            return Path(argv[i + 1]).expanduser()
        if a.startswith("--runs-root="):
            return Path(a.split("=", 1)[1]).expanduser()
        i += 1
    return None


def _bootstrap_scheme_phase_runs_env(argv: list[str]) -> None:
    """If ``--runs-root`` is present, set ``INVERST_SCHEME_PHASE_RUNS`` before importing ``core``."""
    parsed = _parse_runs_root_from_argv(argv)
    if parsed is not None:
        os.environ["INVERST_SCHEME_PHASE_RUNS"] = str(parsed.resolve())


sys.path.insert(0, str(REPO_ROOT))
_bootstrap_scheme_phase_runs_env(sys.argv)

warnings.filterwarnings("ignore", message=".*LibreSSL.*")

try:
    from core.config import settings as app_settings
    from core.scheme_paths import WORKSPACE_ROOT as SCHEME_RUNS_ROOT
    from core.execution_agent import run_ide_execution_agent
    from core.execution_prep import prepare_execution_workspace
    from core.external_coder_handoff import validate_external_coder_completion, write_external_coder_handoff
    from core.health_reports import write_run_level_health
    from core.llm import LLMCompletionError, LLMService
    from core.scheme_agent import (
        get_default_scheme_project_name,
        get_scheme_phase_default_agent_model,
        review_scheme_package,
        revise_scheme_session,
        run_scheme_agent,
        warn_if_implicit_default_project_with_session,
    )
    from core.workspace_git import checkout_workspace_branch, commit_workspace_changes, ensure_workspace_clean
except ModuleNotFoundError as e:
    mod = str(getattr(e, "name", "") or "").strip() or "unknown"
    if mod == "core" or mod.startswith("core."):
        raise SystemExit(
            f"Import failed for internal module ({mod!r}). "
            "Run from the repository root so `core/` is on PYTHONPATH, or set PYTHONPATH to the repo root."
        ) from e
    hint = "PyYAML (`python3 -m pip install pyyaml`)" if mod == "yaml" else f"`python3 -m pip install {mod}`"
    raise SystemExit(
        "Missing dependency: "
        + mod
        + ". Install via "
        + hint
        + " or `python3 -m pip install -r requirements.txt`, then rerun."
    ) from e

import yaml


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cfg(external_coder: str) -> dict[str, Any]:
    return {
        "mode": "autonomy_loop",
        "external_coder": external_coder or None,
    }


def _write_heartbeat(*, session_dir: Path, payload: dict[str, Any]) -> None:
    out_dir = session_dir / "project" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "autonomy_heartbeat.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log = out_dir / "autonomy_heartbeat.jsonl"
    log.write_text(log.read_text(encoding="utf-8", errors="replace") + json.dumps(payload, ensure_ascii=False) + "\n" if log.exists() else json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_autonomy_config() -> dict[str, Any]:
    cfg_path = REPO_ROOT / "config" / "agents.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    cfg = data.get("autonomy")
    return cfg if isinstance(cfg, dict) else {}


def _resolve_scheduler_model(cli_model: str | None, *, external_coder_model: str) -> tuple[str, str]:
    if cli_model is not None and str(cli_model).strip():
        return str(cli_model).strip(), "cli"
    env = (os.environ.get("INVERST_AUTONOMY_SCHEDULER_MODEL") or "").strip()
    if env:
        return env, "env_INVERST_AUTONOMY_SCHEDULER_MODEL"
    cfg = _load_autonomy_config()
    if isinstance(cfg, dict):
        raw = (cfg.get("scheduler_model") or "").strip()
        if raw:
            return raw, "agents_yaml_autonomy.scheduler_model"
    fb = get_scheme_phase_default_agent_model()
    if fb == (external_coder_model or "").strip():
        return "gpt-oss:120b", "fallback_hardcoded_scheduler"
    return fb, "fallback_scheme_phase_default_agent_model"


def _resolve_scheduler_timeout_seconds(cli_timeout: int | None) -> tuple[int, str]:
    if cli_timeout is not None and int(cli_timeout) > 0:
        return int(cli_timeout), "cli"
    env = (os.environ.get("INVERST_AUTONOMY_SCHEDULER_TIMEOUT_SECONDS") or "").strip()
    if env:
        try:
            return max(10, int(env, 10)), "env_INVERST_AUTONOMY_SCHEDULER_TIMEOUT_SECONDS"
        except ValueError:
            pass
    cfg = _load_autonomy_config()
    if isinstance(cfg, dict):
        v = cfg.get("scheduler_timeout_seconds")
        if v is not None:
            try:
                return max(10, int(v)), "agents_yaml_autonomy.scheduler_timeout_seconds"
            except (TypeError, ValueError):
                pass
    return 120, "default"


def _scheduler_compose_external_coder_task(
    *,
    llm: LLMService,
    model: str,
    timeout_seconds: int,
    session_dir: Path,
    base_task: str,
    issues: list[str],
) -> str:
    issues_block = "\n".join(f"- {x}" for x in issues if str(x).strip())
    system = (
        "You are the Scheduler (operator agent). Your job: write one concise instruction block for an external coding agent.\n"
        "Constraints:\n"
        "- Focus on evidence and verification. Do not write code yourself.\n"
        "- Be short and actionable. Use imperative steps.\n"
        "- Assume the external agent will read the handoff JSON and scheme artifacts.\n"
        "Output only the instruction text.\n"
    )
    user = "\n".join(
        [
            "Context:",
            f"- session_dir: {session_dir}",
            "- required outputs: project/outputs/execution_report.md, project/outputs/review_gate.md, project/outputs/completion_evidence.json",
            "- completion evidence must list verification.commands_run and include at least one python/pytest command",
            "",
            "Base task:",
            base_task.strip() or "(none)",
            "",
            "Known issues from last attempt (must fix):" if issues_block else "Known issues from last attempt:",
            issues_block or "(none)",
            "",
            "Write a minimal next-step plan. If issues exist, the plan must begin by fixing them. End with a short verification command list.",
        ]
    )
    try:
        msg = llm.chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=model,
            temperature=0.0,
            timeout=timeout_seconds,
        )
        out = str(getattr(msg, "content", "") or "").strip()
        return out if out else (base_task.strip() or "")
    except LLMCompletionError:
        return (base_task.strip() or "") + ("\n\n" + issues_block if issues_block else "")


def _dispatch_external_coder(
    *,
    command_template: str,
    handoff_path: Path,
    session_dir: Path,
    external_coder: str,
    external_coder_model: str,
    timeout_seconds: int | None,
    extra_path_dirs: list[str],
) -> dict[str, Any]:
    tpl = (command_template or "").strip()
    if not tpl:
        return {
            "status": "external_coder_dispatch_failed",
            "reason_code": "external_coder_command_template_empty",
            "message": "external coder command template is empty",
        }
    cmd = tpl.format(
        handoff_path=str(handoff_path),
        session_dir=str(session_dir),
        project_dir=str(session_dir / "project"),
        artifacts_dir=str(session_dir / "artifacts"),
        external_coder=str(external_coder),
        external_coder_model=str(external_coder_model or ""),
    )
    env = dict(os.environ)
    if extra_path_dirs:
        env["PATH"] = ":".join([*extra_path_dirs, env.get("PATH", "")])
    try:
        cp = subprocess.run(
            cmd,
            shell=True,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "external_coder_dispatch_failed",
            "reason_code": "external_coder_dispatch_timeout",
            "message": "external coder command timed out",
            "command": cmd,
        }
    if int(cp.returncode) != 0:
        return {
            "status": "external_coder_dispatch_failed",
            "reason_code": "external_coder_dispatch_nonzero_exit",
            "message": "external coder command failed",
            "command": cmd,
            "exit_code": int(cp.returncode),
            "stdout_tail": str(cp.stdout or "")[-1200:],
            "stderr_tail": str(cp.stderr or "")[-1200:],
        }
    return {
        "status": "external_coder_dispatched",
        "reason_code": "external_coder_dispatched",
        "message": "external coder command dispatched successfully",
        "command": cmd,
        "exit_code": int(cp.returncode),
        "stdout_tail": str(cp.stdout or "")[-1200:],
        "stderr_tail": str(cp.stderr or "")[-1200:],
    }


def _validate_external_coder_completion(*, session_dir: Path) -> dict[str, Any]:
    return validate_external_coder_completion(session_dir=session_dir)


def _refined_task_text(scheme_result: dict[str, Any]) -> str:
    r = scheme_result.get("refined_task") if isinstance(scheme_result.get("refined_task"), dict) else {}
    return str(r.get("task_text") or "").strip()


def _load_refined_task_from_session(session_dir: Path) -> str:
    p = session_dir / "artifacts" / "refined_task.json"
    if not p.is_file():
        return ""
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, dict):
            return str(data.get("task_text") or data.get("task") or "").strip()
    except (json.JSONDecodeError, OSError):
        pass
    return ""


def _load_post_ide_feedback(session_dir: Path, extra_path: Path | None, *, max_chars: int = 16000) -> str:
    parts: list[str] = []
    per = max(2000, max_chars // 3)
    for rel in ("project/outputs/execution_report.md", "project/outputs/review_gate.md"):
        fp = session_dir / rel
        if fp.is_file():
            t = fp.read_text(encoding="utf-8", errors="replace")
            parts.append(f"--- {rel} ---\n{t[:per]}")
    if extra_path is not None and extra_path.is_file():
        t = extra_path.read_text(encoding="utf-8", errors="replace")
        parts.append(f"--- {extra_path} ---\n{t[:per]}")
    return "\n\n".join(parts).strip()


def _run_scheme_review_loop(
    *,
    session_dir: Path,
    task_for_review: str,
    scheme_model: str,
    review_model: str,
    output_lang: str,
    skip: bool,
    review_inner_max_rounds: int,
    max_revision_attempts: int,
    revision_max_rounds: int,
    verbose: bool,
) -> dict[str, Any]:
    task = (task_for_review or "").strip() or "(scheme task)"
    if skip:
        return {
            "ok": True,
            "skipped": True,
            "review_history": [],
            "last_review": {"can_proceed": True, "issues": [], "suggestions": []},
            "revision_attempts": 0,
        }

    history: list[dict[str, Any]] = []
    for attempt in range(max_revision_attempts + 1):
        rr = review_scheme_package(
            task=task,
            run_root=session_dir,
            review_model=review_model,
            output_lang=output_lang,
            max_rounds=review_inner_max_rounds,
            verbose=verbose,
        )
        rev_payload = rr.get("review") if isinstance(rr.get("review"), dict) else {}
        if str(rr.get("status") or "") == "error":
            history.append({"attempt": attempt, "review": rr})
            return {
                "ok": False,
                "review_history": history,
                "last_review": rev_payload,
                "revision_attempts": attempt,
                "reason": "review_llm_error",
            }
        can_proceed = bool(rev_payload.get("can_proceed", False))
        history.append({"attempt": attempt, "review": rr})
        if can_proceed:
            return {"ok": True, "review_history": history, "last_review": rev_payload, "revision_attempts": attempt}
        if attempt >= max_revision_attempts:
            return {
                "ok": False,
                "review_history": history,
                "last_review": rev_payload,
                "revision_attempts": attempt,
                "reason": "max_revision_attempts",
            }
        issues = rev_payload.get("issues") if isinstance(rev_payload.get("issues"), list) else []
        sugs = rev_payload.get("suggestions") if isinstance(rev_payload.get("suggestions"), list) else []
        fb_lines = (
            ["## Blocking issues"]
            + [f"- {x}" for x in issues]
            + ["## Suggestions"]
            + [f"- {x}" for x in sugs]
        )
        fb = "\n".join(str(x) for x in fb_lines)
        if not fb.strip():
            fb = "Address the scheme package so the external review can set can_proceed to true."
        rs = revise_scheme_session(
            scheme_session_dir=session_dir,
            feedback_text=fb,
            feedback_source="autonomy_scheme_review",
            model=scheme_model,
            output_lang=output_lang,
            max_rounds=revision_max_rounds,
            verbose=verbose,
        )
        history.append({"revision_after_attempt": attempt, "revise": rs})
        if str(rs.get("status") or "") not in ("success", "partial"):
            return {
                "ok": False,
                "review_history": history,
                "last_review": rev_payload,
                "revision_attempts": attempt,
                "reason": "revise_failed",
                "revise": rs,
            }
    return {
        "ok": False,
        "review_history": history,
        "last_review": {},
        "revision_attempts": max_revision_attempts,
        "reason": "exhausted",
    }


def main() -> None:
    sys.stderr.write(
        "WARNING: scripts/run_autonomy_loop.py is DEPRECATED. "
        "Use scripts/run_research_session.py or scripts/run_scheme_then_ide.py instead.\n\n"
    )
    p = argparse.ArgumentParser(
        description=(
            "Autonomy loop: scheme → package review (revise until pass) → prep → IDE; optional post-IDE workflow iterations."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("task", nargs="*", help="User request for the scheme phase")
    p.add_argument("--project", default=get_default_scheme_project_name())
    p.add_argument("--session", default="")
    p.add_argument("--resume-latest", action="store_true")
    p.add_argument(
        "--runs-root",
        default=None,
        metavar="DIR",
        help=(
            "Scheme output root: contains <project>/<session>/ trees (env INVERST_SCHEME_PHASE_RUNS). "
            "Parsed from argv before core imports; use this flag or set the env var before python. "
            f"Default if env unset: {_DEFAULT_GENERATED_PROJECTS_ROOT}"
        ),
    )
    p.add_argument(
        "--workspace-root",
        default="",
        help=(
            "Workspace root for execution prep + IDE (session dir must be under it for default prep paths). "
            "Default: same as scheme runs root (--runs-root / INVERST_SCHEME_PHASE_RUNS), not the repo cwd."
        ),
    )
    p.add_argument("--lang", choices=("en", "zh"), default="en")
    p.add_argument("--allow-ideate", action="store_true")
    p.add_argument("--scheme-model", default="")
    p.add_argument("--scheme-max-rounds", type=int, default=400)
    p.add_argument("--scheme-stall-exit-rounds", type=int, default=20)
    p.add_argument("--scheme-llm-timeout-seconds", type=int, default=120)
    p.add_argument("--scheme-run-time-budget-seconds", type=int, default=0)
    p.add_argument("--scheme-retry-cap", type=int, default=2)

    p.add_argument(
        "--skip-scheme-review",
        action="store_true",
        help="Skip review_scheme_package / revise_scheme_session gate; prep+IDE run after scheme success only.",
    )
    p.add_argument(
        "--scheme-review-model",
        default="",
        help="Model for package review JSON (default: same as --scheme-model).",
    )
    p.add_argument(
        "--scheme-review-inner-rounds",
        type=int,
        default=2,
        help="Max inner LLM rounds per review_scheme_package call.",
    )
    p.add_argument(
        "--scheme-review-revision-max",
        type=int,
        default=4,
        help="Max times to call revise_scheme_session after a blocking review before giving up.",
    )
    p.add_argument(
        "--scheme-revision-agent-max-rounds",
        type=int,
        default=18,
        help="Max agent rounds per revise_scheme_session call.",
    )
    p.add_argument(
        "--max-workflow-iterations",
        type=int,
        default=1,
        help=(
            "After a successful IDE pass, optionally run another workflow: read post-IDE outputs, revise scheme, "
            "re-review, prep, IDE again. Values >1 require artifacts under project/outputs/."
        ),
    )
    p.add_argument(
        "--iteration-feedback-file",
        default="",
        metavar="PATH",
        help="Optional extra text file appended to post-IDE feedback for workflow iterations (wf>=1).",
    )

    p.add_argument("--skip-execution-prep", action="store_true")
    p.add_argument("--execution-output-subdir", default="")

    p.add_argument("--ide-model", default="")
    p.add_argument("--ide-task", default="")
    p.add_argument("--ide-supplement", action="store_true")
    p.add_argument("--ide-max-rounds", type=int, default=400)
    p.add_argument("--ide-run-time-budget-seconds", type=int, default=0)
    p.add_argument("--ide-retry-cap", type=int, default=6)

    p.add_argument("--external-coder", default="cline")
    p.add_argument("--auto-run-external-coder", action="store_true")
    p.add_argument("--external-coder-retry-cap", type=int, default=6)
    p.add_argument("--external-coder-command-template", default="")
    p.add_argument("--external-coder-timeout-seconds", type=int, default=0)
    p.add_argument("--external-coder-model", default="")
    p.add_argument("--built-in-ide", action="store_true")

    p.add_argument("--scheduler-model", default="", help="Scheduler/orchestrator model used to generate retry instructions (must differ from coder model)")
    p.add_argument("--scheduler-timeout-seconds", type=int, default=0, help="Timeout for scheduler LLM calls")

    p.add_argument("--workspace-git-branch", default="")
    p.add_argument("--workspace-git-require-clean", action="store_true")
    p.add_argument("--workspace-git-dirty-strategy", choices=("auto_commit", "fail"), default="auto_commit")
    p.add_argument("--workspace-git-commit", action="store_true")
    p.add_argument("--workspace-git-commit-message", default="")

    p.add_argument("--autonomy-run-time-budget-seconds", type=int, default=0)
    p.add_argument("--heartbeat-interval-seconds", type=int, default=180)
    p.add_argument(
        "--max-cycles",
        type=int,
        default=200,
        help="Max IDE/external-coder retries **within one workflow** after prep (not scheme re-runs).",
    )
    p.add_argument("-q", "--quiet", action="store_true")

    args = p.parse_args()
    verbose = not args.quiet

    wr = Path(args.workspace_root).resolve() if (args.workspace_root or "").strip() else SCHEME_RUNS_ROOT
    try:
        SCHEME_RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    if args.session and args.project == get_default_scheme_project_name():
        warn_if_implicit_default_project_with_session(
            project_name=str(args.project),
            session_name=str(args.session).strip() or None,
            stream=sys.stderr,
        )

    started = time.monotonic()
    total_budget = int(args.autonomy_run_time_budget_seconds) or 0

    def remaining_budget() -> int | None:
        if total_budget <= 0:
            return None
        elapsed = int(time.monotonic() - started)
        return max(0, total_budget - elapsed)

    external_coder = "" if args.built_in_ide else str(args.external_coder or "").strip().lower()
    out: dict[str, Any] = {
        "paths": {
            "repo_root": str(REPO_ROOT),
            "scheme_runs_root": str(SCHEME_RUNS_ROOT),
            "workspace_root": str(wr),
        },
    }
    attempts: list[dict[str, Any]] = []
    workspace_git: dict[str, Any] = {}
    session_dir: Path | None = None
    last_issues: list[str] = []
    scheduler_llm = LLMService()

    scheme_task = " ".join(args.task).strip()
    scheme_model = (args.scheme_model or "").strip() or get_scheme_phase_default_agent_model()
    review_model = (args.scheme_review_model or "").strip() or scheme_model
    review_inner = max(1, int(args.scheme_review_inner_rounds))
    max_rev_attempts = max(0, int(args.scheme_review_revision_max))
    revision_max_rounds = max(1, int(args.scheme_revision_agent_max_rounds))
    max_wf = max(1, int(args.max_workflow_iterations))
    extra_iter_fb = Path((args.iteration_feedback_file or "").strip()).expanduser() if (args.iteration_feedback_file or "").strip() else None

    scheme_result: dict[str, Any] = {}

    for workflow_idx in range(max_wf):
        rb = remaining_budget()
        if rb is not None and rb <= 0:
            out["autonomy_exit_reason"] = "autonomy_budget_exhausted"
            break

        if workflow_idx == 0:
            if session_dir is None:
                scheme_retry_cap = max(0, int(args.scheme_retry_cap))
                for i in range(scheme_retry_cap + 1):
                    rb = remaining_budget()
                    scheme_budget = int(args.scheme_run_time_budget_seconds) or 0
                    if rb is not None and scheme_budget > 0:
                        scheme_budget = min(scheme_budget, rb)
                    scheme_result = run_scheme_agent(
                        task=scheme_task,
                        model=scheme_model,
                        output_lang=str(args.lang),
                        run_root=None,
                        project_name=str(args.project),
                        session_name=(str(args.session).strip() or None),
                        resume_latest=bool(args.resume_latest),
                        max_rounds=int(args.scheme_max_rounds),
                        stall_exit_rounds=(int(args.scheme_stall_exit_rounds) or None),
                        allow_ideate=bool(args.allow_ideate),
                        verbose=verbose,
                        llm_timeout_seconds=int(args.scheme_llm_timeout_seconds),
                        run_time_budget_seconds=(scheme_budget or None),
                    )
                    attempts.append({"phase": "scheme", "attempt": i + 1, "status": str(scheme_result.get("status") or ""), "reason_code": str(scheme_result.get("status_reason_code") or "")})
                    if str(scheme_result.get("status") or "") != "partial":
                        break
                out["scheme"] = scheme_result
                run_root_s = str(scheme_result.get("run_root") or "").strip()
                if not run_root_s:
                    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
                    raise SystemExit(2)
                session_dir = Path(run_root_s).resolve()

                hb0 = {
                    "schema_version": "autonomy_heartbeat_v1",
                    "generated_at": _utc_now(),
                    "workflow": workflow_idx,
                    "cycle": 0,
                    "phase": "scheme",
                    "status": str(scheme_result.get("status") or ""),
                    "status_reason_code": str(scheme_result.get("status_reason_code") or ""),
                    "remaining_budget_seconds": rb,
                }
                _write_heartbeat(session_dir=session_dir, payload=hb0)

                st_scheme = str(scheme_result.get("status") or "")
                if st_scheme in ("rejected", "error"):
                    break
                if st_scheme != "success":
                    out["autonomy_exit_reason"] = "scheme_not_success_before_execution"
                    out["autonomy_exit_detail"] = {
                        "scheme_status": st_scheme,
                        "scheme_reason_code": str(scheme_result.get("status_reason_code") or ""),
                        "hint": "Fix task/rounds and re-run, or continue the same session via run_scheme_agent; execution runs only after scheme status is success.",
                    }
                    break

            scheme_result = out.get("scheme") if isinstance(out.get("scheme"), dict) else scheme_result
            task_for_review = _refined_task_text(scheme_result) or scheme_task
            rr_out = _run_scheme_review_loop(
                session_dir=session_dir,
                task_for_review=task_for_review,
                scheme_model=scheme_model,
                review_model=review_model,
                output_lang=str(args.lang),
                skip=bool(args.skip_scheme_review),
                review_inner_max_rounds=review_inner,
                max_revision_attempts=max_rev_attempts,
                revision_max_rounds=revision_max_rounds,
                verbose=verbose,
            )
            if not rr_out.get("ok"):
                out["scheme_review"] = rr_out
                out["autonomy_exit_reason"] = "scheme_review_blocked"
                break
            out["scheme_review"] = rr_out
        else:
            assert session_dir is not None
            fb_text = _load_post_ide_feedback(session_dir, extra_iter_fb)
            if not fb_text.strip():
                out["autonomy_note"] = f"workflow_iteration_{workflow_idx}_skipped_empty_feedback"
                break
            rs_pi = revise_scheme_session(
                scheme_session_dir=session_dir,
                feedback_text=fb_text,
                feedback_source="autonomy_post_ide_iteration",
                model=scheme_model,
                output_lang=str(args.lang),
                max_rounds=revision_max_rounds,
                verbose=verbose,
            )
            out.setdefault("scheme_post_ide_revisions", []).append({"workflow": workflow_idx, "revise": rs_pi})
            task_for_review = _load_refined_task_from_session(session_dir) or scheme_task
            rr_pi = _run_scheme_review_loop(
                session_dir=session_dir,
                task_for_review=task_for_review,
                scheme_model=scheme_model,
                review_model=review_model,
                output_lang=str(args.lang),
                skip=bool(args.skip_scheme_review),
                review_inner_max_rounds=review_inner,
                max_revision_attempts=max_rev_attempts,
                revision_max_rounds=revision_max_rounds,
                verbose=verbose,
            )
            key = f"scheme_review_w{workflow_idx}"
            if not rr_pi.get("ok"):
                out[key] = rr_pi
                out["autonomy_exit_reason"] = "scheme_review_blocked_post_ide"
                break
            out[key] = rr_pi

        assert session_dir is not None

        branch_name = (args.workspace_git_branch or "").strip()
        if branch_name:
            workspace_git["branch"] = checkout_workspace_branch(session_dir=session_dir, branch=branch_name)
        if args.workspace_git_require_clean:
            workspace_git["clean_check"] = ensure_workspace_clean(session_dir=session_dir)
            clean_status = str((workspace_git.get("clean_check") or {}).get("status") or "")
            if clean_status == "dirty" and str(args.workspace_git_dirty_strategy) == "auto_commit":
                pre_msg = (args.workspace_git_commit_message or "").strip() or "auto-clean before run"
                workspace_git["preflight_commit"] = commit_workspace_changes(session_dir=session_dir, message=pre_msg)
                workspace_git["clean_check_after_autofix"] = ensure_workspace_clean(session_dir=session_dir)
                clean_status = str((workspace_git.get("clean_check_after_autofix") or {}).get("status") or "")
            if clean_status != "clean":
                out["workspace_git"] = workspace_git
                out["ide"] = {
                    "status": "rejected_workspace_git_dirty",
                    "status_reason_code": "workspace_git_dirty",
                    "status_reason_message": "workspace git tree is not clean (--workspace-git-require-clean)",
                }
                break

        if not args.skip_execution_prep:
            osd = (args.execution_output_subdir or "").strip() or None
            prep_workspace_root = wr
            if osd is None:
                try:
                    _ = session_dir.relative_to(wr)
                except ValueError:
                    prep_workspace_root = session_dir.parent
            out["execution_prep"] = prepare_execution_workspace(
                scheme_session_dir=session_dir,
                workspace_root=prep_workspace_root,
                output_subdir=osd,
            )

        ide_result: dict[str, Any] = {}
        ide_success = False
        last_issues = []

        for cycle in range(max(1, int(args.max_cycles))):
            rb = remaining_budget()
            if rb is not None and rb <= 0:
                break

            if external_coder:
                scheme = out.get("scheme") if isinstance(out.get("scheme"), dict) else {}
                refined = (scheme or {}).get("refined_task") if isinstance((scheme or {}).get("refined_task"), dict) else {}
                cmd_tpl = (
                    (args.external_coder_command_template or "").strip()
                    or (os.environ.get("INVERST_EXTERNAL_CODER_COMMAND_TEMPLATE") or "").strip()
                    or str(getattr(getattr(app_settings, "runtime", None), "external_coder_command_template", "") or "").strip()
                )
                extra_path_dirs = list(getattr(getattr(app_settings, "paths", None), "tool_bin_dirs", []) or [])
                external_retry_cap = max(0, int(args.external_coder_retry_cap))
                base_task = str(args.ide_task or "").strip()
                scheduler_model, scheduler_model_source = _resolve_scheduler_model(
                    str(args.scheduler_model or "").strip() or None,
                    external_coder_model=(
                        (args.external_coder_model or "").strip()
                        or str(getattr(getattr(app_settings, "runtime", None), "external_coder_model", "") or "").strip()
                    ),
                )
                scheduler_timeout, scheduler_timeout_source = _resolve_scheduler_timeout_seconds(
                    int(args.scheduler_timeout_seconds) if int(args.scheduler_timeout_seconds) > 0 else None
                )

                ide_result = {"status": "skipped_external_coder", "external_coder": external_coder}
                for i in range(external_retry_cap + 1):
                    retry_task = _scheduler_compose_external_coder_task(
                        llm=scheduler_llm,
                        model=scheduler_model,
                        timeout_seconds=scheduler_timeout,
                        session_dir=session_dir,
                        base_task=base_task,
                        issues=last_issues,
                    )
                    ide_result["scheduler_model"] = scheduler_model
                    ide_result["scheduler_model_source"] = scheduler_model_source
                    ide_result["scheduler_timeout_seconds"] = scheduler_timeout
                    ide_result["scheduler_timeout_source"] = scheduler_timeout_source
                    handoff_path = write_external_coder_handoff(
                        session_dir=session_dir,
                        external_coder=external_coder,
                        task=retry_task,
                        refined_task=refined,
                        include_acceptance=True,
                    )
                    ide_result["external_handoff_path"] = str(handoff_path)
                    if not args.auto_run_external_coder:
                        ide_result["status"] = "skipped_external_coder"
                        ide_result["reason_code"] = "external_coder_mode"
                        break
                    timeout_seconds = int(args.external_coder_timeout_seconds) or 0
                    if rb is not None and timeout_seconds > 0:
                        timeout_seconds = min(timeout_seconds, rb)
                    dispatch = _dispatch_external_coder(
                        command_template=cmd_tpl,
                        handoff_path=handoff_path,
                        session_dir=session_dir,
                        external_coder=external_coder,
                        external_coder_model=(
                            (args.external_coder_model or "").strip()
                            or str(getattr(getattr(app_settings, "runtime", None), "external_coder_model", "") or "").strip()
                        ),
                        timeout_seconds=(timeout_seconds or None),
                        extra_path_dirs=extra_path_dirs,
                    )
                    ide_result.update(dispatch)
                    if str(ide_result.get("status") or "") == "external_coder_dispatched":
                        verify = _validate_external_coder_completion(session_dir=session_dir)
                        ide_result["completion_check"] = verify
                        if str(verify.get("status") or "") == "external_coder_completed":
                            ide_result["status"] = "external_coder_completed"
                            ide_result["reason_code"] = str(verify.get("reason_code") or "external_coder_completion_verified")
                            ide_result["message"] = str(verify.get("message") or "external coder completion contract verified")
                            last_issues = []
                            break
                        ide_result["status"] = str(verify.get("status") or "external_coder_incomplete")
                        ide_result["reason_code"] = str(verify.get("reason_code") or "external_coder_completion_missing_artifacts")
                        ide_result["message"] = str(verify.get("message") or "external coder completion contract not satisfied")
                        issues = verify.get("issues")
                        last_issues = [str(x) for x in (issues if isinstance(issues, list) else []) if str(x).strip()]
                    attempts.append({"phase": "ide", "attempt": i + 1, "status": str(ide_result.get("status") or ""), "reason_code": str(ide_result.get("reason_code") or "")})
                    if str(ide_result.get("status") or "") == "external_coder_completed":
                        break
                    hb = {
                        "schema_version": "autonomy_heartbeat_v1",
                        "generated_at": _utc_now(),
                        "workflow": workflow_idx,
                        "cycle": cycle,
                        "phase": "ide_external_coder",
                        "attempt": i + 1,
                        "status": str(ide_result.get("status") or ""),
                        "reason_code": str(ide_result.get("reason_code") or ""),
                        "issues": last_issues,
                        "remaining_budget_seconds": remaining_budget(),
                    }
                    _write_heartbeat(session_dir=session_dir, payload=hb)
                    if i < external_retry_cap:
                        time.sleep(max(1, int(args.heartbeat_interval_seconds)))

                out["ide"] = ide_result
                if args.workspace_git_commit:
                    workspace_git["commit"] = commit_workspace_changes(session_dir=session_dir, message=(args.workspace_git_commit_message or "").strip())
                if workspace_git:
                    out["workspace_git"] = workspace_git
                write_run_level_health(session_dir=session_dir, out=out, attempts=attempts, config=_cfg(external_coder), final_decision="autonomy_loop")
                if str(ide_result.get("status") or "") == "external_coder_completed":
                    ide_success = True
                    break
                if not args.auto_run_external_coder:
                    break
                continue

            ide_retry_cap = max(0, int(args.ide_retry_cap))
            for i in range(ide_retry_cap + 1):
                ide_budget = int(args.ide_run_time_budget_seconds) or 0
                if rb is not None and ide_budget > 0:
                    ide_budget = min(ide_budget, rb)
                ide_result = run_ide_execution_agent(
                    task=(args.ide_task or "").strip(),
                    task_mode="supplement" if args.ide_supplement else "override",
                    scheme_session_dir=session_dir,
                    workspace_root=wr,
                    model=(args.ide_model or "").strip() or None,
                    max_rounds=int(args.ide_max_rounds),
                    run_time_budget_seconds=(ide_budget or None),
                    verbose=verbose,
                )
                attempts.append({"phase": "ide", "attempt": i + 1, "status": str(ide_result.get("status") or ""), "reason_code": str((ide_result.get("runtime_summary") or {}).get("status_reason_code") or "")})
                hb = {
                    "schema_version": "autonomy_heartbeat_v1",
                    "generated_at": _utc_now(),
                    "workflow": workflow_idx,
                    "cycle": cycle,
                    "phase": "ide_built_in",
                    "attempt": i + 1,
                    "status": str(ide_result.get("status") or ""),
                    "remaining_budget_seconds": remaining_budget(),
                }
                _write_heartbeat(session_dir=session_dir, payload=hb)
                if str(ide_result.get("status") or "") not in ("stalled", "partial", "rejected_completion"):
                    break
                time.sleep(max(1, int(args.heartbeat_interval_seconds)))
            out["ide"] = ide_result
            if args.workspace_git_commit:
                workspace_git["commit"] = commit_workspace_changes(session_dir=session_dir, message=(args.workspace_git_commit_message or "").strip())
            if workspace_git:
                out["workspace_git"] = workspace_git
            write_run_level_health(session_dir=session_dir, out=out, attempts=attempts, config=_cfg(external_coder), final_decision="autonomy_loop")
            if str(ide_result.get("status") or "") == "success":
                ide_success = True
                break

        out.setdefault("workflows", []).append({"workflow": workflow_idx, "ide": ide_result, "ide_success": ide_success})
        if not ide_success:
            break
        if workflow_idx + 1 >= max_wf:
            break

    if session_dir is not None:
        write_run_level_health(session_dir=session_dir, out=out, attempts=attempts, config=_cfg(external_coder), final_decision="autonomy_loop_exit")
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    ide = out.get("ide") if isinstance(out.get("ide"), dict) else {}
    scheme = out.get("scheme") if isinstance(out.get("scheme"), dict) else {}
    scheme_status = str((scheme or {}).get("status") or "")
    ide_status = str((ide or {}).get("status") or "")
    exit_reason = str(out.get("autonomy_exit_reason") or "")
    fatal_review = exit_reason in ("scheme_review_blocked", "scheme_review_blocked_post_ide")
    ok_ide = ide_status in ("success", "external_coder_completed", "skipped_external_coder")
    if scheme_status not in ("success",) or not ok_ide or fatal_review:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
