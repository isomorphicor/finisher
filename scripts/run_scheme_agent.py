#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.execution_prep import prepare_execution_workspace
from core.scheme_agent import (
    get_default_scheme_project_name,
    get_scheme_phase_default_agent_model,
    review_scheme_package,
    revise_scheme_session,
    run_scheme_agent,
    warn_if_implicit_default_project_with_session,
)
from runtime.router.intent_router import IntentRouter
from runtime.runtime_factory import build_runtime

REQUIRED_SCHEME_ARTIFACTS = (
    "research_plan.md",
    "derivation.md",
    "architecture_draft.md",
    "experiment_design.md",
)

# Progress score: pure scheme prose (four md files, no structured scheme outputs) cannot exceed this.
SCHEME_ONLY_MAX_SCORE = 60
# Unlock >60 only if empirical_anchor >= this. Max anchor without JSON is 15+10=25 (numbers+grounding), so 28
# effectively requires scheme_summary.json and/or experiment_matrix.json (CLI) or future evidence hooks.
EMPIRICAL_GATE_MIN_ANCHOR = 28


def _compute_artifact_fingerprint(run_root: Path) -> str | None:
    artifacts_dir = run_root / "artifacts"
    if not artifacts_dir.is_dir():
        return None
    blobs: list[bytes] = []
    for name in REQUIRED_SCHEME_ARTIFACTS:
        p = artifacts_dir / name
        if not p.is_file():
            return None
        blobs.append(p.read_bytes())
    h = hashlib.sha256()
    for b in blobs:
        h.update(b)
        h.update(b"\n---\n")
    return h.hexdigest()


def _artifact_texts(run_root: Path) -> dict[str, str]:
    artifacts_dir = run_root / "artifacts"
    out: dict[str, str] = {}
    for name in REQUIRED_SCHEME_ARTIFACTS:
        p = artifacts_dir / name
        out[name] = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    return out


def _empirical_anchor_score(*, run_root: Path, texts: dict[str, str]) -> tuple[int, dict[str, int]]:
    """Concrete grounding: numerics, optional JSON artifacts, data/metric vocabulary (max 35)."""
    combined = "\n".join(texts.get(n, "") for n in REQUIRED_SCHEME_ARTIFACTS)
    cl = combined.lower()
    numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", combined)
    nn = len(numbers)
    if nn >= 45:
        npt = 15
    elif nn >= 25:
        npt = 12
    elif nn >= 12:
        npt = 8
    elif nn >= 6:
        npt = 4
    else:
        npt = 0

    adir = run_root / "artifacts"
    spt = 0
    if (adir / "scheme_summary.json").is_file():
        spt += 5
    if (adir / "experiment_matrix.json").is_file():
        spt += 5

    patterns = (
        r"\.csv\b",
        r"\.parquet\b",
        r"\bparquet\b",
        r"\bpandas\b",
        r"\bpolars\b",
        r"\bsql\b",
        r"\bschema\b",
        r"\bfeature\b",
        r"\blabel\b",
        r"\btarget\b",
        r"\btrain\b",
        r"\bvalid\b",
        r"\btest\b",
        r"\bsplit\b",
        r"\bfold\b",
        r"\bmse\b",
        r"\brmse\b",
        r"\bmae\b",
        r"\bauc\b",
        r"\br2\b",
        r"\br²\b",
        r"\bsharpe\b",
        r"\bic\b",
        r"\baic\b",
        r"\bbic\b",
        r"\bsample\b",
        r"\bcohort\b",
    )
    gh = sum(1 for p in patterns if re.search(p, cl))
    if gh >= 12:
        gpt = 10
    elif gh >= 7:
        gpt = 7
    elif gh >= 4:
        gpt = 4
    else:
        gpt = 0

    raw = npt + spt + gpt
    total = min(35, raw)
    return total, {"numbers_15": npt, "structure_10": spt, "grounding_10": gpt}


def _scheme_quality_and_novelty(*, experiment_design: str, architecture_draft: str) -> tuple[int, int]:
    """Stricter than keyword OR: require compositional signals so templates cannot max trivially."""
    exp_l = experiment_design.lower()
    arch_l = architecture_draft.lower()
    blob = exp_l + "\n" + arch_l

    quality = 0
    has_accept = ("pass condition" in exp_l) or ("acceptance" in exp_l) or ("acceptance criteria" in exp_l)
    has_threshold = bool(re.search(r"[\d>%]|bps|basis\s*point|threshold|metric\s+criterion", exp_l))
    if has_accept and has_threshold:
        quality += 10
    elif has_accept:
        quality += 4

    val_words = (
        "oos path",
        "out-of-sample",
        "out of sample",
        "cpcv",
        "walk-forward",
        "walk forward",
        "purged",
        "embargo",
        "combinatorial",
    )
    has_val = any(w in exp_l for w in val_words)
    has_split_detail = bool(re.search(r"\b(fold|split|horizon|window|bar|period)\b", exp_l))
    if has_val and has_split_detail:
        quality += 10
    elif has_val:
        quality += 4

    g1 = any(k in blob for k in ("hypothesis", "ablation", "baseline", "counterfactual", "falsif"))
    g2 = any(k in blob for k in ("matrix", "grid", "sweep", "factorial"))
    g3 = any(k in blob for k in ("novel", "alternative", "variant", "compared to"))
    n_groups = sum((g1, g2, g3))
    if n_groups >= 2:
        novelty = 10
    elif n_groups == 1:
        novelty = 4
    else:
        novelty = 0

    return quality, novelty


def _progress_score(*, run_root: Path, run_status: str, prev_fingerprint: str | None) -> tuple[int, dict[str, int], dict[str, bool]]:
    texts = _artifact_texts(run_root)
    all_present = all(bool(texts.get(n)) for n in REQUIRED_SCHEME_ARTIFACTS)
    fp = _compute_artifact_fingerprint(run_root)
    changed = bool(fp and prev_fingerprint and fp != prev_fingerprint)
    first_success = bool(fp and not prev_fingerprint)

    # 40 points: completeness
    completeness = 40 if (run_status == "success" and all_present) else 0

    # 30 points: material delta vs previous
    delta = 30 if (changed or first_success) else 0

    exp = texts.get("experiment_design.md", "")
    arch = texts.get("architecture_draft.md", "")
    quality, novelty = _scheme_quality_and_novelty(experiment_design=exp, architecture_draft=arch)

    empirical_anchor, anchor_parts = _empirical_anchor_score(run_root=run_root, texts=texts)
    # Penalize "four files filled with prose" with no numerics, data/metric hooks, or structured outputs.
    speculation_penalty = max(0, 35 - empirical_anchor)

    raw_subtotal = completeness + delta + quality + novelty
    pre_cap_total = max(0, min(100, raw_subtotal - speculation_penalty))
    total = pre_cap_total
    empirical_gate_passed = empirical_anchor >= EMPIRICAL_GATE_MIN_ANCHOR
    if not empirical_gate_passed:
        total = min(total, SCHEME_ONLY_MAX_SCORE)

    breakdown = {
        "completeness_40": completeness,
        "delta_30": delta,
        "quality_20": quality,
        "novelty_10": novelty,
        "empirical_anchor_35": empirical_anchor,
        "speculation_penalty": speculation_penalty,
        "pre_cap_total": pre_cap_total,
        "scheme_only_cap_applied": int(pre_cap_total > total),
        "empirical_gate_min_anchor": EMPIRICAL_GATE_MIN_ANCHOR,
        "scheme_only_max_score": SCHEME_ONLY_MAX_SCORE,
        **anchor_parts,
    }
    flags = {
        "all_required_artifacts_present": all_present,
        "fingerprint_changed": changed,
        "first_success_for_project": first_success,
        "major_update_candidate": total >= 85,
        "empirical_grounding_strong": empirical_anchor >= 28,
        "speculative_scheme_risk": empirical_anchor < 15,
        "empirical_gate_passed": empirical_gate_passed,
        "scheme_only_cap_applied": bool(pre_cap_total > total),
    }
    return total, breakdown, flags


def _artifact_fingerprint_already_logged(log_path: Path, fingerprint: str) -> bool:
    """True if this four-artifact fingerprint already appears on any line (stops duplicate session re-runs after log edits)."""
    if not fingerprint or not log_path.is_file():
        return False
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("artifact_fingerprint") or "") == fingerprint:
            return True
    return False


def _load_last_project_entry(log_path: Path, project: str) -> dict[str, object] | None:
    if not log_path.is_file():
        return None
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None
    for line in reversed(lines):
        raw = line.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("project") or "") == project:
            return data
    return None


def _should_update_knowledge(
    *,
    run_status: str,
    run_root: Path,
    project: str,
) -> tuple[bool, str, str | None, int, dict[str, int], dict[str, bool]]:
    if run_status != "success":
        return False, "run_not_success", None, 0, {}, {"major_update_candidate": False}
    fp = _compute_artifact_fingerprint(run_root)
    if not fp:
        return False, "missing_required_artifacts", None, 0, {}, {"major_update_candidate": False}
    log_path = REPO_ROOT / "knowledge" / "decision_log.jsonl"
    prev = _load_last_project_entry(log_path, project)
    prev_fp = str(prev.get("artifact_fingerprint") or "") if prev else None
    score, breakdown, flags = _progress_score(run_root=run_root, run_status=run_status, prev_fingerprint=prev_fp)
    if score < 70:
        return False, "progress_score_below_threshold", fp, score, breakdown, flags
    if _artifact_fingerprint_already_logged(log_path, fp):
        return False, "artifact_fingerprint_already_in_knowledge_log", fp, score, breakdown, flags
    if not prev:
        if not bool(flags.get("major_update_candidate")):
            return False, "first_project_run_below_major_threshold", fp, score, breakdown, flags
        return True, "first_success_for_project", fp, score, breakdown, flags
    if str(prev.get("artifact_fingerprint") or "") == fp:
        return False, "no_material_change", fp, score, breakdown, flags
    # New artifact bytes almost every run; without an extra gate, every success would append.
    # Only promote follow-up runs when the progress score indicates a major update (doc: >= 85).
    if not bool(flags.get("major_update_candidate")):
        return False, "below_major_update_threshold", fp, score, breakdown, flags
    return True, "artifact_fingerprint_changed", fp, score, breakdown, flags


def _value_score_and_failure_pattern(*, progress_score: int, score_breakdown: dict[str, int], progress_flags: dict[str, bool]) -> tuple[int, str | None]:
    # Map progress score (0-100) to a compact value score (0-10).
    value_score = max(0, min(10, int(round(progress_score / 10.0))))

    # Keep tags aligned with knowledge/failure_patterns.md
    if not bool(progress_flags.get("all_required_artifacts_present")):
        return value_score, "incomplete_research_package"
    if int(score_breakdown.get("empirical_anchor_35", 0)) < 28 and bool(progress_flags.get("all_required_artifacts_present")):
        return value_score, "speculative_without_empirical_anchors"
    if int(score_breakdown.get("quality_20", 0)) < 10:
        return value_score, "weak_acceptance_definition"
    if int(score_breakdown.get("novelty_10", 0)) == 0:
        return value_score, "low_novelty_direction"
    if progress_score < 70:
        return value_score, "low_progress_iteration"
    return value_score, None


def _append_decision_log_draft(
    *,
    task: str,
    project: str,
    session: str,
    run_status: str,
    run_root: str,
    artifact_fingerprint: str,
    update_reason: str,
    progress_score: int,
    score_breakdown: dict[str, int],
    progress_flags: dict[str, bool],
) -> None:
    knowledge_dir = REPO_ROOT / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    log_path = knowledge_dir / "decision_log.jsonl"
    now = datetime.now(timezone.utc)
    value_score, failure_pattern = _value_score_and_failure_pattern(
        progress_score=progress_score,
        score_breakdown=score_breakdown,
        progress_flags=progress_flags,
    )
    entry = {
        "date": now.strftime("%Y-%m-%d"),
        "decision_id": f"run-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "topic": "scheme run",
        "status": "accepted" if run_status == "success" else "rejected",
        "rationale": f"Scheme run for project '{project}', session '{session}'.",
        "project": project,
        "session": session,
        "task_excerpt": (task or "")[:240],
        "run_status": run_status,
        "run_root": run_root,
        "artifact_fingerprint": artifact_fingerprint,
        "update_reason": update_reason,
        "progress_score": progress_score,
        "score_breakdown": score_breakdown,
        "progress_flags": progress_flags,
        "value_score": value_score,
        "failure_pattern": failure_pattern,
        "evidence_ids": [],
        "replaces": [],
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _run_post_tools(*, repo_root: Path, workspace_root: Path, specs: list[str], verbose: bool) -> list[dict[str, object]]:
    runtime = build_runtime(workspace_root=workspace_root, backend="local")
    router = IntentRouter(repo_root=repo_root, runtime=runtime)
    outputs: list[dict[str, object]] = []
    for i, raw in enumerate(specs, start=1):
        spec = json.loads(raw)
        intent = str(spec.get("intent") or "").strip()
        arguments = spec.get("args") or {}
        out = router.route(intent=intent, arguments=arguments)
        outputs.append({"index": i, "intent": intent, "output": out})
        if verbose:
            print(f"[post-tool:{i}] intent={intent} status={out.get('status')}")
        if out.get("status") != "success":
            break
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous scheme agent (tool skills + self-directed workflow).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Examples: docs/guides/command_examples.md — scheme phase: docs/experiments/scheme_phase/blueprint.md",
    )
    g_run = parser.add_argument_group("Task & session")
    g_run.add_argument("task", nargs="*", help="User request (ignored with --revision)")
    g_run.add_argument(
        "--model",
        type=str,
        default=None,
        help="Main LLM (default: config/agents.yaml scheme_phase.default_agent_model, or env INVERST_SCHEME_AGENT_MODEL)",
    )
    g_run.add_argument("--lang", type=str, default="en", choices=("en", "zh"), help="Artifact language")
    g_run.add_argument(
        "--project",
        type=str,
        default=get_default_scheme_project_name(),
        help="Top-level folder: <runs_root>/<project>/ (not the session name). Default: env INVERST_DEFAULT_SCHEME_PROJECT or 'default'",
    )
    g_run.add_argument(
        "--session",
        type=str,
        default="",
        help="Session segment: …/<project>/<session>/; omit → main (or INVERST_DEFAULT_SCHEME_SESSION=timestamp for UTC dir)",
    )
    g_run.add_argument("--run-dir", type=str, default=None, help="Fixed session dir (skips project/session layout)")
    g_run.add_argument("--resume-latest", action="store_true", help="Continue latest session under --project")
    g_run.add_argument("--max-rounds", type=int, default=30, help="Max tool rounds")
    g_run.add_argument("--allow-ideate", action="store_true", help="If task is empty, let the agent invent one")
    g_run.add_argument("-q", "--quiet", action="store_true", help="Less log output")

    g_gate = parser.add_argument_group("Gates & review")
    g_gate.add_argument("--no-refine", action="store_true", help="Skip refine_user_need_to_task")
    g_gate.add_argument("--no-topic-gate", action="store_true", help="Skip topic alignment gate")
    g_gate.add_argument("--max-review-rounds", type=int, default=2, help="Reviewer / topic-gate retry rounds")
    g_gate.add_argument("--review-model", type=str, default=None, help="JSON reviewer (topic gate, optional summary); also runs extra review_scheme_package after success if set")
    g_gate.add_argument(
        "--reviewer-models",
        type=str,
        default="",
        help="Comma-separated models → env INVERST_SCHEME_REVIEWER_MODELS (overrides config/agents hiring)",
    )

    g_models = parser.add_argument_group("Extra model overrides")
    g_models.add_argument("--refine-model", type=str, default="", help="Refine step (default: --model)")
    g_models.add_argument("--topic-gate-model", type=str, default="", help="Topic gate only (default: hired reviewer or --model)")
    g_models.add_argument("--summary-model", type=str, default="", help="scheme_summary.json (default: reviewer or --model)")
    g_models.add_argument("--translate-model", type=str, default="", help="ZH translation (default: --refine-model or --model)")

    g_out = parser.add_argument_group("Artifacts & translation")
    g_out.add_argument("--emit-json-summary", action="store_true", help="Write artifacts/scheme_summary.json")
    g_out.add_argument(
        "--emit-experiment-matrix",
        action="store_true",
        help="Write experiment_matrix.json (implies --emit-json-summary; needs summary JSON first)",
    )
    g_out.add_argument("--no-translate-output", action="store_true", help="Keep design English when --lang zh")
    g_out.add_argument("--no-auto-hire", action="store_true", help="Do not pick reviewer/translator from config/agents.yaml")

    g_rev = parser.add_argument_group("Revise existing session")
    g_rev.add_argument("--revision", action="store_true", help="Rewrite artifacts from --feedback (needs --run-dir)")
    g_rev.add_argument("--feedback", type=str, default="", help="Feedback file for --revision")

    g_post = parser.add_argument_group("After run")
    g_post.add_argument("--auto-execution-prep", action="store_true", help="Copy scheme artifacts into workspace for execution")
    g_post.add_argument("--workspace-root", type=str, default=".", help="For execution prep and --run-tool-spec")
    g_post.add_argument(
        "--execution-output-subdir",
        type=str,
        default="",
        help="execution prep under workspace-root (legacy). Empty = <session>/project/execution_prep/ (INVERST_EXECUTION_PREP_TIMESTAMP=1 for timestamp subdir).",
    )
    g_post.add_argument(
        "--no-log-knowledge",
        action="store_true",
        help="Skip knowledge/decision_log.jsonl evaluation (default: score artifacts and append only when worth updating)",
    )
    g_post.add_argument(
        "--run-tool-spec",
        action="append",
        default=[],
        metavar="JSON",
        help='Post-run routed tool, e.g. {"intent":"terminal.run","args":{"command":"pytest"}} (repeatable)',
    )

    args = parser.parse_args()
    if not args.run_dir and not args.quiet:
        warn_if_implicit_default_project_with_session(
            project_name=args.project,
            session_name=(args.session.strip() or None),
            stream=sys.stderr,
        )
    scheme_model = (args.model or "").strip() or get_scheme_phase_default_agent_model()
    emit_json_summary = bool(args.emit_json_summary) or bool(args.emit_experiment_matrix)

    # If user provides no task, the scheme agent should ideate one autonomously.
    task = " ".join(args.task).strip() if args.task else ""
    if (not task) and (not args.revision) and (not args.allow_ideate):
        raise SystemExit("Empty task. Provide a task string, or pass --allow-ideate to let the agent ideate one.")
    run_root = Path(args.run_dir).resolve() if args.run_dir else None
    verbose = not args.quiet
    if args.reviewer_models.strip():
        os.environ["INVERST_SCHEME_REVIEWER_MODELS"] = args.reviewer_models.strip()

    if args.revision:
        if not run_root:
            raise SystemExit("--revision requires --run-dir pointing to an existing scheme session dir")
        fb_path = (args.feedback or "").strip()
        if not fb_path:
            raise SystemExit("--revision requires --feedback <file>")
        fb_text = Path(fb_path).read_text(encoding="utf-8", errors="replace")
        result = revise_scheme_session(
            scheme_session_dir=run_root,
            feedback_text=fb_text,
            feedback_source=fb_path,
            model=scheme_model,
            output_lang=args.lang,
            design_lang="en",
            max_rounds=args.max_rounds,
            translate_output=(not args.no_translate_output),
            translate_model=(args.translate_model.strip() or None),
            verbose=verbose,
        )
    else:
        result = run_scheme_agent(
            task=task,
            model=scheme_model,
            output_lang=args.lang,
            design_lang="en",
            run_root=run_root,
            project_name=args.project,
            session_name=(args.session.strip() or None),
            resume_latest=bool(args.resume_latest),
            max_rounds=args.max_rounds,
            review_model=args.review_model,
            max_review_rounds=args.max_review_rounds,
            enable_refine=(not args.no_refine),
            enable_topic_gate=(not args.no_topic_gate),
            allow_ideate=bool(args.allow_ideate),
            refine_model=(args.refine_model.strip() or None),
            topic_gate_model=(args.topic_gate_model.strip() or None),
            emit_json_summary=emit_json_summary,
            summary_model=(args.summary_model.strip() or None),
            emit_experiment_matrix=bool(args.emit_experiment_matrix),
            translate_output=(not args.no_translate_output),
            translate_model=(args.translate_model.strip() or None),
            auto_hire=(not args.no_auto_hire),
            verbose=verbose,
        )
    print(f"Run dir: {result.get('run_root')}")
    print(f"Status: {result.get('status')}")
    if result.get("missing"):
        print(f"Missing: {result.get('missing')}")

    if args.review_model and result.get("run_root"):
        rev = review_scheme_package(
            task=task,
            run_root=Path(result["run_root"]).resolve(),
            review_model=args.review_model,
            output_lang=args.lang,
            max_rounds=args.max_review_rounds,
            verbose=verbose,
        )
        print("Review:", rev.get("review"))

    if args.auto_execution_prep and result.get("status") == "success" and result.get("run_root"):
        prep = prepare_execution_workspace(
            scheme_session_dir=Path(result["run_root"]).resolve(),
            workspace_root=Path(args.workspace_root).resolve(),
            output_subdir=(args.execution_output_subdir or "").strip() or None,
        )
        print("Execution prep:", json.dumps(prep, ensure_ascii=False, sort_keys=True))

    if args.run_tool_spec:
        tool_outputs = _run_post_tools(
            repo_root=REPO_ROOT,
            workspace_root=Path(args.workspace_root).resolve(),
            specs=list(args.run_tool_spec),
            verbose=verbose,
        )
        print("Post tools:", json.dumps(tool_outputs, ensure_ascii=False, sort_keys=True))

    if (not args.no_log_knowledge) and result.get("run_root"):
        session = (args.session.strip() or Path(str(result.get("run_root"))).name)
        run_root_path = Path(str(result.get("run_root"))).resolve()
        should_log, reason, fp, score, score_breakdown, progress_flags = _should_update_knowledge(
            run_status=str(result.get("status") or ""),
            run_root=run_root_path,
            project=args.project,
        )
        if not args.quiet:
            print(
                "Knowledge update (auto gate):",
                json.dumps(
                    {"score": score, "reason": reason, "breakdown": score_breakdown, "flags": progress_flags},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )
        if should_log and fp:
            _append_decision_log_draft(
                task=task,
                project=args.project,
                session=session,
                run_status=str(result.get("status") or ""),
                run_root=str(result.get("run_root") or ""),
                artifact_fingerprint=fp,
                update_reason=reason,
                progress_score=score,
                score_breakdown=score_breakdown,
                progress_flags=progress_flags,
            )
            if args.quiet:
                print(f"Knowledge log appended ({reason})")
            elif verbose:
                print(f"Knowledge log appended: {reason}")
        elif verbose:
            print(f"Knowledge log not appended: {reason}")


if __name__ == "__main__":
    main()
