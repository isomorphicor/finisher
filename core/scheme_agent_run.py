"""Scheme agent main loop: run, revise, and external review."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.experiment_matrix import build_experiment_matrix_from_scheme_summary
from core.experiment_utils import missing_artifacts_in_dir, output_lang_instruction
from core.llm import LLMCompletionError, LLMService
from core.refine import extract_data_path_anchors, merge_data_path_anchors_into_refined, refine_user_need_to_task
from core.scheme_contract import REQUIRED_SCHEME_ARTIFACTS, SCHEME_SUMMARY_SCHEMA_VERSION
from core.scheme_gates import _topic_alignment_gate
from core.scheme_package_io import _gather_scheme_package, _safe_json_loads
from core.scheme_paths import _run_dir
from core.scheme_phase_models import (
    _load_scheme_phase_hiring_config,
    _pick_reviewer_model,
    _pick_reviewer_models,
    _pick_translator_model,
)
from core.scheme_policy_skills import (
    _ideate_quant_task,
    _load_policy_skill_injections,
    _load_quant_soul_text,
    _looks_quant_related,
)
from core.scheme_prompts import (
    SCHEME_AGENT_SYSTEM,
    SCHEME_REVISION_SYSTEM,
    SCHEME_SUMMARY_SYSTEM,
    SIMPLE_REVIEW_SYSTEM,
)
from core.translate import translate_text, translate_to_english_if_needed
from skills.scheme_phase import get_scheme_phase_tools


def _scheme_progress_signature(run_root: Path) -> str:
    h = hashlib.sha256()
    ad = run_root / "artifacts"
    for name in REQUIRED_SCHEME_ARTIFACTS:
        p = ad / name
        h.update(name.encode())
        h.update(p.read_bytes() if p.is_file() else b"")
    return h.hexdigest()


def run_scheme_agent(
    *,
    task: str,
    model: str,
    output_lang: str = "en",
    design_lang: str = "en",
    run_root: Path | None = None,
    project_name: str = "default",
    session_name: str | None = None,
    resume_latest: bool = False,
    max_rounds: int = 30,
    review_model: str | None = None,
    max_review_rounds: int = 2,
    enable_refine: bool = True,
    enable_topic_gate: bool = True,
    allow_ideate: bool = False,
    refine_model: str | None = None,
    topic_gate_model: str | None = None,
    emit_json_summary: bool = False,
    summary_model: str | None = None,
    emit_experiment_matrix: bool = False,
    translate_output: bool = True,
    translate_model: str | None = None,
    auto_hire: bool = True,
    verbose: bool = True,
    llm_timeout_seconds: int | None = None,
    run_time_budget_seconds: int | None = None,
    stall_exit_rounds: int | None = None,
) -> dict[str, Any]:
    design_lang = "en"
    if llm_timeout_seconds is not None:
        try:
            llm_timeout = max(1, int(llm_timeout_seconds))
        except (TypeError, ValueError):
            llm_timeout = 300
    else:
        llm_timeout = 300
    run_root = (run_root or _run_dir(project_name=project_name, session_name=session_name, resume_latest=resume_latest)).resolve()
    artifacts_dir = run_root / "artifacts"
    existing_missing = missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)
    if (not existing_missing) and artifacts_dir.is_dir():
        refined0: dict[str, Any] = {}
        refined_path = artifacts_dir / "refined_task.json"
        if refined_path.is_file():
            try:
                refined0 = json.loads(refined_path.read_text(encoding="utf-8", errors="replace"))
                refined0 = refined0 if isinstance(refined0, dict) else {}
            except Exception:
                refined0 = {}
        if not enable_topic_gate:
            return {
                "status": "success",
                "run_root": str(run_root),
                "missing": [],
                "final": "",
                "refined_task": refined0,
                "warnings": ["finalized_existing_session"],
            }
        topic_path = artifacts_dir / "topic_alignment.json"
        if topic_path.is_file():
            try:
                gate = json.loads(topic_path.read_text(encoding="utf-8", errors="replace"))
                gate = gate if isinstance(gate, dict) else {}
            except Exception:
                gate = {}
            blocking = bool(gate.get("blocking_issues")) or bool(gate.get("must_fix"))
            if bool(gate.get("on_topic", False)) and (not blocking):
                return {
                    "status": "success",
                    "run_root": str(run_root),
                    "missing": [],
                    "final": "",
                    "refined_task": refined0,
                    "warnings": ["finalized_existing_session"],
                }
    hiring_cfg = _load_scheme_phase_hiring_config() if auto_hire else {}
    if auto_hire and (hiring_cfg.get("auto_hire") is False):
        hiring_cfg = {}

    hired_reviewers = _pick_reviewer_models(hiring_cfg) if hiring_cfg else []
    hired_reviewer = hired_reviewers[0] if hired_reviewers else (_pick_reviewer_model(hiring_cfg) if hiring_cfg else None)
    hired_translator = _pick_translator_model(hiring_cfg) if hiring_cfg else None
    if hired_reviewer and not review_model:
        review_model = hired_reviewer
    if hired_reviewer and not topic_gate_model:
        topic_gate_model = hired_reviewer
    if hired_reviewer and emit_json_summary and not summary_model:
        summary_model = hired_reviewer
    if hired_translator and translate_output and output_lang in ("zh",) and not translate_model:
        translate_model = hired_translator
    allowed_write_paths = {f"artifacts/{n}" for n in REQUIRED_SCHEME_ARTIFACTS}
    tools_spec, tools_impl = get_scheme_phase_tools(run_root, allowed_write_paths=allowed_write_paths)
    llm = LLMService()

    lang_inst = output_lang_instruction(design_lang if design_lang in ("zh", "en") else "en")
    system = SCHEME_AGENT_SYSTEM + lang_inst
    refined: dict[str, Any] | None = None
    task_for_design = (task or "").strip()
    if not task_for_design:
        if not allow_ideate:
            return {
                "status": "rejected",
                "report": {},
                "errors": [{"code": "E_EMPTY_TASK", "message": "empty task; ideation disabled", "details": {"allow_ideate": False}}],
            }
        try:
            task_for_design = _ideate_quant_task(llm=llm, model=(refine_model or model), timeout=120)
        except Exception:
            task_for_design = "Propose and validate a simple baseline factor model for cross-sectional stock returns with strict time-safety gates."
        (run_root / "artifacts" / "ideated_task.json").write_text(
            json.dumps({"schema_version": "ideated_task_v1", "task_text": task_for_design}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if design_lang == "en":
        try:
            task_for_design = translate_to_english_if_needed(
                text=task_for_design,
                model=(translate_model or refine_model or model),
            )
        except Exception:
            pass
    if enable_refine:
        try:
            refined = refine_user_need_to_task(raw_need=task_for_design, model=(refine_model or model), output_lang=design_lang)
            refined = merge_data_path_anchors_into_refined(raw_need=task_for_design, refined=refined)
            rt = str(refined.get("task_text") or "") if isinstance(refined, dict) else ""
            still_missing = [a for a in extract_data_path_anchors(task_for_design) if a and a not in rt]
            if still_missing:
                refined = merge_data_path_anchors_into_refined(raw_need=task_for_design, refined=refined)
                rt = str(refined.get("task_text") or "")
                still_missing = [a for a in extract_data_path_anchors(task_for_design) if a and a not in rt]
            if still_missing:
                (run_root / "artifacts" / "refine_warning.json").write_text(
                    json.dumps(
                        {
                            "schema_version": "refine_warning_v1",
                            "warning": "could not merge some data path anchors into refined task_text",
                            "missing_anchors": still_missing,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            (run_root / "artifacts" / "refined_task.json").write_text(json.dumps(refined, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            refined = None

    literature_block = ""
    try:
        literature_block = _presearch_literature(refined=refined, fallback_query=task_for_design)
    except Exception:
        literature_block = ""

    if refined and refined.get("task_text"):
        user = "Refined task (single source of truth):\n\n" + str(refined.get("task_text")) + "\n\nUser raw request:\n\n" + task_for_design
        if refined.get("non_goals"):
            user += "\n\nNon-goals:\n" + "\n".join(f"- {x}" for x in refined.get("non_goals", [])[:20])
        if refined.get("deliverables"):
            user += "\n\nDeliverables:\n" + "\n".join(f"- {x}" for x in refined.get("deliverables", [])[:20])
        if refined.get("constraints"):
            user += "\n\nConstraints:\n" + "\n".join(f"- {x}" for x in refined.get("constraints", [])[:20])
    else:
        user = f"User request:\n\n{task_for_design}"
    if literature_block:
        user += "\n\nRetrieved literature (use as evidence; cite key ideas, do not hallucinate citations):\n\n" + literature_block
    quant_soul = ""
    quant_related = _looks_quant_related(task_for_design) or (refined and _looks_quant_related(str(refined.get("task_text") or "")))
    if quant_related:
        quant_soul = _load_quant_soul_text()
    if quant_soul:
        user += "\n\nQuant Soul (hard gates for quant tasks; must comply):\n\n" + quant_soul

    # MD policy skills (NanoClaw-inspired): optional prompt injections
    try:
        policy_blocks = _load_policy_skill_injections(task_text=task_for_design, quant_related=bool(quant_related))
    except Exception:
        policy_blocks = []
    if policy_blocks:
        joined = "\n\n---\n\n".join(policy_blocks)
        user += "\n\nPolicy Skills (MD; must comply when applicable):\n\n" + joined
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        stall_lim = int(stall_exit_rounds) if stall_exit_rounds is not None and int(stall_exit_rounds) > 0 else None
    except (TypeError, ValueError):
        stall_lim = None
    try:
        budget_s = int(run_time_budget_seconds) if run_time_budget_seconds is not None and int(run_time_budget_seconds) > 0 else None
    except (TypeError, ValueError):
        budget_s = None
    (run_root / "artifacts" / "run_config.json").write_text(
        json.dumps(
            {
                "schema_version": "scheme_agent_run_config_v1",
                "model": model,
                "refine_model": refine_model or model,
                "topic_gate_model": topic_gate_model or review_model or model,
                "summary_model": summary_model or review_model or model,
                "translate_model": translate_model or refine_model or model,
                "output_lang": output_lang,
                "design_lang": design_lang,
                "enable_refine": bool(enable_refine),
                "enable_topic_gate": bool(enable_topic_gate),
                "emit_json_summary": bool(emit_json_summary),
                "emit_experiment_matrix": bool(emit_experiment_matrix),
                "translate_output": bool(translate_output),
                "auto_hire": bool(auto_hire),
                "hired": {
                    "reviewer_models": hired_reviewers,
                    "translator_model": hired_translator,
                },
                "max_rounds": int(max_rounds),
                "llm_timeout_seconds": llm_timeout,
                "run_time_budget_seconds": budget_s,
                "stall_exit_rounds": stall_lim,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    topic_gate_passed = not enable_topic_gate

    scheme_t0 = time.monotonic()
    stall_prev_sig: str | None = None
    stall_count = 0

    def _tick_scheme_stall() -> dict[str, Any] | None:
        nonlocal stall_prev_sig, stall_count
        if stall_lim is None:
            return None
        sig = _scheme_progress_signature(run_root)
        if stall_prev_sig is not None and sig == stall_prev_sig:
            stall_count += 1
            if stall_count >= stall_lim:
                missing = missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)
                return {
                    "status": "partial",
                    "run_root": str(run_root),
                    "missing": missing,
                    "refined_task": refined or {},
                    "status_reason_code": "stall_exit",
                    "warnings": [f"scheme_stall_exit_after_{stall_lim}_rounds"],
                }
        else:
            stall_count = 0
        stall_prev_sig = sig
        return None

    for round_no in range(max_rounds):
        if budget_s is not None and (time.monotonic() - scheme_t0) >= budget_s:
            missing = missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)
            return {
                "status": "partial",
                "run_root": str(run_root),
                "missing": missing,
                "refined_task": refined or {},
                "status_reason_code": "run_time_budget",
                "warnings": ["scheme_run_time_budget_exceeded"],
            }
        if verbose:
            print(f"  [scheme-agent round {round_no + 1}/{max_rounds}] {model}...", flush=True)
        try:
            msg = llm.chat_completion(messages, tools=tools_spec, model=model, temperature=0.3, timeout=llm_timeout)
        except LLMCompletionError as e:
            (run_root / "artifacts" / "last_error.json").write_text(
                json.dumps(
                    {
                        "schema_version": "scheme_agent_error_v1",
                        "error": str(e),
                        "model": model,
                        "round": round_no + 1,
                        "llm_timeout_seconds": llm_timeout,
                        "message_count": len(messages),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            missing = missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)
            if (not missing) and (topic_gate_passed or (not enable_topic_gate)):
                return {
                    "status": "success",
                    "run_root": str(run_root),
                    "missing": [],
                    "final": "",
                    "refined_task": refined or {},
                    "warnings": ["llm_call_failed_but_artifacts_complete"],
                }
            return {
                "status": "partial",
                "run_root": str(run_root),
                "missing": missing,
                "error": str(e),
                "refined_task": refined or {},
            }

        tcs = getattr(msg, "tool_calls", None) or []
        if not tcs:
            missing = missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)
            if verbose and (not missing):
                print(
                    "  [scheme-agent] model returned no tool calls; running completion gates (not counted as a new round)...",
                    flush=True,
                )
            if missing:
                messages.append({"role": "assistant", "content": getattr(msg, "content", None) or ""})
                messages.append(
                    {
                        "role": "user",
                        "content": "Missing required artifacts: "
                        + ", ".join(missing)
                        + ". Call write_file for each missing path under artifacts/; do not end the run with text only until all four files exist.",
                    }
                )
                st_exit = _tick_scheme_stall()
                if st_exit is not None:
                    return st_exit
                continue
            if (not missing) and enable_topic_gate and (not topic_gate_passed):
                if topic_gate_model:
                    gate_models = [topic_gate_model]
                elif review_model:
                    gate_models = [review_model]
                else:
                    gate_models = hired_reviewers or [model]
                try:
                    gate = _topic_alignment_gate(
                        run_root=run_root,
                        refined=(refined or {"task_text": task}),
                        models=gate_models,
                        output_lang=output_lang,
                        quant_related=bool(quant_related),
                        verbose=verbose,
                        llm_timeout_seconds=llm_timeout,
                    )
                except Exception:
                    gate = {"on_topic": True, "blocking_issues": [], "must_fix": [], "missing_terms": [], "notes": []}
                (run_root / "artifacts" / "topic_alignment.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
                blocking = bool(gate.get("blocking_issues")) or bool(gate.get("must_fix"))
                if gate.get("on_topic") and (not blocking):
                    topic_gate_passed = True
                else:
                    messages.append({"role": "assistant", "content": getattr(msg, "content", None) or ""})
                    fix = "\n".join(f"- {x}" for x in (gate.get("must_fix") or [])[:12])
                    issues = "\n".join(f"- {x}" for x in (gate.get("blocking_issues") or [])[:12])
                    missing_terms = ", ".join((gate.get("missing_terms") or [])[:20])
                    messages.append(
                        {
                            "role": "user",
                            "content": "Gate failed. Revise the four artifacts to satisfy blocking issues and must-fix items (stay on the refined task).\n\nBlocking issues:\n"
                            + (issues or "- (none)")
                            + "\n\nMust fix:\n"
                            + (fix or "- (none)")
                            + ("\n\nMissing terms: " + missing_terms if missing_terms else ""),
                        }
                    )
                    st_exit = _tick_scheme_stall()
                    if st_exit is not None:
                        return st_exit
                    continue
            if (not missing) and emit_json_summary:
                sm = summary_model or review_model or model
                if verbose:
                    print(
                        f"  [scheme-agent] emit_json_summary (extra LLM, timeout {llm_timeout}s)...",
                        flush=True,
                    )
                try:
                    pkg = _gather_scheme_package(run_root, max_chars=120000)
                    refined_payload = refined or {"task_text": task, "key_terms": []}
                    user = json.dumps({"refined_task": refined_payload, "scheme_package": pkg}, ensure_ascii=False)
                    msg2 = llm.chat_completion(
                        messages=[
                            {"role": "system", "content": SCHEME_SUMMARY_SYSTEM + lang_inst},
                            {"role": "user", "content": user},
                        ],
                        model=sm,
                        temperature=0.2,
                        response_format={"type": "json_object"},
                        timeout=llm_timeout,
                    )
                    data2 = _safe_json_loads((getattr(msg2, "content", None) or "").strip() if msg2 else "") or {}
                    if "schema_version" not in data2:
                        data2["schema_version"] = SCHEME_SUMMARY_SCHEMA_VERSION
                    (run_root / "artifacts" / "scheme_summary.json").write_text(json.dumps(data2, ensure_ascii=False, indent=2), encoding="utf-8")
                    if emit_experiment_matrix:
                        built = build_experiment_matrix_from_scheme_summary(data2)
                        (run_root / "artifacts" / "experiment_matrix.json").write_text(json.dumps(built.matrix, ensure_ascii=False, indent=2), encoding="utf-8")
                        if not built.ok:
                            (run_root / "artifacts" / "experiment_matrix_errors.json").write_text(json.dumps({"errors": built.errors}, ensure_ascii=False, indent=2), encoding="utf-8")
                except LLMCompletionError as e:
                    (run_root / "artifacts" / "scheme_summary_error.json").write_text(
                        json.dumps(
                            {"schema_version": "scheme_summary_error_v1", "error": str(e), "model": sm},
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                except Exception as e:
                    (run_root / "artifacts" / "scheme_summary_error.json").write_text(
                        json.dumps(
                            {"schema_version": "scheme_summary_error_v1", "error": repr(e), "model": sm},
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )

            if (not missing) and translate_output and output_lang in ("zh",) and design_lang == "en":
                tm = translate_model or refine_model or model
                try:
                    for fname in REQUIRED_SCHEME_ARTIFACTS:
                        p = run_root / "artifacts" / fname
                        if not p.is_file():
                            continue
                        translated = translate_text(text=p.read_text(encoding="utf-8", errors="replace"), target_lang=output_lang, model=tm)
                        if translated:
                            p.write_text(translated, encoding="utf-8")
                    if refined and refined.get("task_text"):
                        refined_zh = {}
                        for k, v in refined.items():
                            if isinstance(v, str):
                                refined_zh[k] = translate_text(text=v, target_lang=output_lang, model=tm)
                            elif isinstance(v, list):
                                refined_zh[k] = [translate_text(text=str(x), target_lang=output_lang, model=tm) for x in v]
                            else:
                                refined_zh[k] = v
                        (run_root / "artifacts" / f"refined_task_{output_lang}.json").write_text(json.dumps(refined_zh, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

            return {
                "status": "success" if not missing else "partial",
                "run_root": str(run_root),
                "missing": missing,
                "final": (getattr(msg, "content", None) or "").strip(),
                "refined_task": refined or {},
            }

        parse_ok = True
        for tc in tcs:
            fn = getattr(tc, "function", None) or (tc if isinstance(tc, dict) else {})
            args_str = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", "{}")
            try:
                json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
            except (json.JSONDecodeError, TypeError):
                parse_ok = False
                break
        if not parse_ok:
            messages.append({"role": "assistant", "content": getattr(msg, "content", None) or ""})
            messages.append(
                {
                    "role": "user",
                    "content": "Tool call arguments must be valid JSON. Escape quotes/backslashes and retry the same tool call(s).",
                }
            )
            st_exit = _tick_scheme_stall()
            if st_exit is not None:
                return st_exit
            continue

        asst: dict[str, Any] = {"role": "assistant", "content": getattr(msg, "content", None) or ""}
        asst["tool_calls"] = []
        for t in tcs:
            t_dict = t.model_dump() if hasattr(t, "model_dump") else (t if isinstance(t, dict) else {"id": getattr(t, "id", ""), "function": getattr(t, "function", {})})
            if hasattr(t_dict.get("function"), "name"):
                t_dict["function"] = {"name": getattr(t_dict["function"], "name", ""), "arguments": getattr(t_dict["function"], "arguments", "{}")}
            asst["tool_calls"].append(t_dict)
        messages.append(asst)

        for tc in tcs:
            fn = getattr(tc, "function", None) or (tc if isinstance(tc, dict) else {})
            name = fn.get("name") if isinstance(fn, dict) else getattr(fn, "name", None)
            args_str = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", "{}")
            args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
            tid = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else "")
            impl = tools_impl.get(name) if name else None
            result = impl(**args) if impl else {"status": "rejected", "report": {}, "errors": [{"code": "E_TOOL", "message": "unknown tool", "details": {"name": name}}]}
            messages.append({"role": "tool", "tool_call_id": tid, "content": json.dumps(result, ensure_ascii=False)})
            if verbose:
                head = json.dumps(result, ensure_ascii=False)[:120]
                print(f"    {name}(...) -> {head}...", flush=True)

        st_exit = _tick_scheme_stall()
        if st_exit is not None:
            return st_exit

    return {"status": "partial", "run_root": str(run_root), "missing": missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)}


def _sha256_hex(text: str) -> str:
    h = hashlib.sha256()
    h.update((text or "").encode("utf-8"))
    return h.hexdigest()


def _extract_feedback_items(text: str, *, max_items: int = 40) -> list[str]:
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    items: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith(("-", "*")) and len(s) > 2:
            items.append(s.lstrip("-* ").strip())
            continue
        if re.match(r"^\d+[\.\)]\s+", s):
            items.append(re.sub(r"^\d+[\.\)]\s+", "", s).strip())
            continue
    if not items:
        parts = [p.strip() for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]
        items = parts[:max_items]
    return [x for x in items if x][:max_items]


def _load_base_task_text(run_root: Path) -> str:
    artifacts_dir = run_root / "artifacts"
    refined_path = artifacts_dir / "refined_task.json"
    if refined_path.is_file():
        try:
            data = json.loads(refined_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict) and str(data.get("task_text") or "").strip():
                return str(data.get("task_text")).strip()
        except Exception:
            pass
    ideated_path = artifacts_dir / "ideated_task.json"
    if ideated_path.is_file():
        try:
            data = json.loads(ideated_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict) and str(data.get("task_text") or "").strip():
                return str(data.get("task_text")).strip()
        except Exception:
            pass
    return ""


def revise_scheme_session(
    *,
    scheme_session_dir: Path,
    feedback_text: str,
    feedback_source: str = "",
    model: str,
    output_lang: str = "en",
    design_lang: str = "en",
    max_rounds: int = 18,
    translate_output: bool = True,
    translate_model: str | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    design_lang = "en"
    llm_timeout = 300
    run_root = scheme_session_dir.resolve()
    artifacts_dir = run_root / "artifacts"
    if not artifacts_dir.is_dir():
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_ART_DIR", "message": "missing artifacts dir", "details": {"path": str(artifacts_dir)}}],
        }

    base_task = _load_base_task_text(run_root) or "(unknown task)"
    feedback_for_design = feedback_text
    if design_lang == "en":
        try:
            feedback_for_design = translate_to_english_if_needed(text=feedback_for_design, model=(translate_model or model))
        except Exception:
            feedback_for_design = feedback_text
    feedback_items = _extract_feedback_items(feedback_for_design)
    indexed = [{"id": _sha256_hex(x)[:8], "text": x} for x in feedback_items]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    revision_id = f"rev-{ts}"
    feedback_hash = _sha256_hex(feedback_text)
    feedback_hash_design = _sha256_hex(feedback_for_design)

    (artifacts_dir / "revision_request.json").write_text(
        json.dumps(
            {
                "schema_version": "scheme_revision_request_v1",
                "revision_id": revision_id,
                "created_at": ts,
                "scheme_session_dir": str(run_root),
                "feedback_source": feedback_source,
                "feedback_sha256": feedback_hash,
                "task_text": base_task,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (artifacts_dir / "feedback_index.json").write_text(
        json.dumps(
            {
                "schema_version": "feedback_index_v1",
                "feedback_sha256_raw": feedback_hash,
                "feedback_sha256_design": feedback_hash_design,
                "items": indexed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pre_hashes: dict[str, str] = {}
    for fname in REQUIRED_SCHEME_ARTIFACTS:
        p = artifacts_dir / fname
        pre_hashes[fname] = _sha256_hex(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else ""

    allowed_write_paths = {f"artifacts/{n}" for n in REQUIRED_SCHEME_ARTIFACTS} | {"artifacts/response_to_review.md"}
    tools_spec, tools_impl = get_scheme_phase_tools(run_root, allowed_write_paths=allowed_write_paths)
    llm = LLMService()
    lang_inst = output_lang_instruction(design_lang if design_lang in ("zh", "en") else "en")
    system = SCHEME_REVISION_SYSTEM + lang_inst

    fb_block = "\n".join(f"- [FB:{x['id']}] {x['text']}" for x in indexed) if indexed else "- [FB:00000000] (no structured items; summarize feedback and respond)"
    user = (
        "Original task:\n\n"
        + base_task
        + "\n\nHuman feedback (respond to each item; include its [FB:<id>] tag):\n\n"
        + fb_block
        + "\n\nNotes:\n- Use read_file to inspect existing artifacts before revising.\n- Write response_to_review.md with one section per feedback item.\n"
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    for round_no in range(max_rounds):
        if verbose:
            print(f"  [scheme-revision round {round_no + 1}/{max_rounds}] {model}...", flush=True)
        try:
            msg = llm.chat_completion(messages, tools=tools_spec, model=model, temperature=0.2, timeout=llm_timeout)
        except LLMCompletionError as e:
            (artifacts_dir / "last_error.json").write_text(
                json.dumps(
                    {
                        "schema_version": "scheme_revision_error_v1",
                        "error": str(e),
                        "model": model,
                        "round": round_no + 1,
                        "llm_timeout_seconds": llm_timeout,
                        "message_count": len(messages),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return {"status": "error", "error": str(e), "run_root": str(run_root)}

        tcs = getattr(msg, "tool_calls", None) or []
        if not tcs:
            missing = missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)
            resp_ok = (artifacts_dir / "response_to_review.md").is_file()
            if missing or (not resp_ok):
                messages.append({"role": "assistant", "content": getattr(msg, "content", None) or ""})
                need = []
                if missing:
                    need.append("Missing required artifacts: " + ", ".join(missing))
                if not resp_ok:
                    need.append("Missing: response_to_review.md")
                messages.append({"role": "user", "content": ". ".join(need) + ". Use write_file to create/update them; keep going until nothing is missing."})
                continue
            break

        parse_ok = True
        for tc in tcs:
            fn = getattr(tc, "function", None) or (tc if isinstance(tc, dict) else {})
            args_str = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", "{}")
            try:
                json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
            except (json.JSONDecodeError, TypeError):
                parse_ok = False
                break
        if not parse_ok:
            messages.append({"role": "assistant", "content": getattr(msg, "content", None) or ""})
            messages.append(
                {
                    "role": "user",
                    "content": "Tool call arguments must be valid JSON. Escape quotes/backslashes and retry the same tool call(s).",
                }
            )
            continue

        asst: dict[str, Any] = {"role": "assistant", "content": getattr(msg, "content", None) or ""}
        asst["tool_calls"] = []
        for t in tcs:
            t_dict = t.model_dump() if hasattr(t, "model_dump") else (t if isinstance(t, dict) else {"id": getattr(t, "id", ""), "function": getattr(t, "function", {})})
            if hasattr(t_dict.get("function"), "name"):
                t_dict["function"] = {"name": getattr(t_dict["function"], "name", ""), "arguments": getattr(t_dict["function"], "arguments", "{}")}
            asst["tool_calls"].append(t_dict)
        messages.append(asst)

        for tc in tcs:
            fn = getattr(tc, "function", None) or (tc if isinstance(tc, dict) else {})
            name = fn.get("name") if isinstance(fn, dict) else getattr(fn, "name", None)
            args_str = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", "{}")
            args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
            tid = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else "")
            impl = tools_impl.get(name) if name else None
            result = impl(**args) if impl else {"status": "rejected", "report": {}, "errors": [{"code": "E_TOOL", "message": "unknown tool", "details": {"name": name}}]}
            messages.append({"role": "tool", "tool_call_id": tid, "content": json.dumps(result, ensure_ascii=False)})
            if verbose:
                head = json.dumps(result, ensure_ascii=False)[:120]
                print(f"    {name}(...) -> {head}...", flush=True)

    if translate_output and output_lang in ("zh",) and design_lang == "en":
        tm = translate_model or model
        try:
            for fname in list(REQUIRED_SCHEME_ARTIFACTS) + ["response_to_review.md"]:
                p = artifacts_dir / fname
                if not p.is_file():
                    continue
                translated = translate_text(text=p.read_text(encoding="utf-8", errors="replace"), target_lang=output_lang, model=tm)
                if translated:
                    p.write_text(translated, encoding="utf-8")
        except Exception:
            pass

    missing = missing_artifacts_in_dir(run_root, REQUIRED_SCHEME_ARTIFACTS, None)
    resp_path = artifacts_dir / "response_to_review.md"
    resp_text = resp_path.read_text(encoding="utf-8", errors="replace") if resp_path.is_file() else ""
    missing_fb = [x["id"] for x in indexed if f"[FB:{x['id']}]" not in resp_text]
    gate = {
        "schema_version": "scheme_revision_gate_v1",
        "revision_id": revision_id,
        "created_at": ts,
        "feedback_sha256": feedback_hash,
        "all_feedback_items_responded": not bool(missing_fb),
        "missing_feedback_ids": missing_fb,
        "missing_required_artifacts": missing,
        "has_response_to_review": bool(resp_text.strip()),
        "status": "ok" if (not missing and resp_text.strip() and not missing_fb) else "needs_work",
    }
    (artifacts_dir / "revision_gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")

    post_hashes: dict[str, str] = {}
    for fname in REQUIRED_SCHEME_ARTIFACTS:
        p = artifacts_dir / fname
        post_hashes[fname] = _sha256_hex(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else ""
    (artifacts_dir / "revision_meta.json").write_text(
        json.dumps(
            {
                "schema_version": "scheme_revision_meta_v1",
                "revision_id": revision_id,
                "created_at": ts,
                "pre_sha256": pre_hashes,
                "post_sha256": post_hashes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    ok = (gate.get("status") == "ok")
    return {
        "status": "success" if ok else "partial",
        "run_root": str(run_root),
        "missing": missing,
        "revision_id": revision_id,
        "revision_gate_status": str(gate.get("status") or ""),
    }


def review_scheme_package(
    *,
    task: str,
    run_root: Path,
    review_model: str,
    output_lang: str = "en",
    max_rounds: int = 2,
    verbose: bool = True,
) -> dict[str, Any]:
    llm = LLMService()
    lang_inst = output_lang_instruction(output_lang if output_lang in ("zh", "en") else "en")
    artifacts_text = []
    for n in REQUIRED_SCHEME_ARTIFACTS:
        p = run_root / "artifacts" / n
        if p.is_file():
            artifacts_text.append(f"--- {n} ---\n{p.read_text(encoding='utf-8', errors='replace')}")
    package = "\n\n".join(artifacts_text)[:90000]
    user = f"User task:\n\n{task}\n\nScheme package:\n\n{package}"
    messages = [{"role": "system", "content": SIMPLE_REVIEW_SYSTEM + lang_inst}, {"role": "user", "content": user}]
    last: dict[str, Any] | None = None
    for i in range(max_rounds):
        if verbose:
            print(f"  [review {i + 1}/{max_rounds}] {review_model}...", flush=True)
        try:
            msg = llm.chat_completion(messages, model=review_model, temperature=0.2, response_format={"type": "json_object"}, timeout=300)
            raw = (getattr(msg, "content", None) or "").strip()
        except LLMCompletionError as e:
            return {"status": "error", "review": {"can_proceed": False, "issues": [str(e)], "suggestions": []}}
        data = _safe_json_loads(raw) or {}
        issues = data.get("issues") if isinstance(data.get("issues"), list) else []
        suggestions = data.get("suggestions") if isinstance(data.get("suggestions"), list) else []
        last = {"can_proceed": bool(data.get("can_proceed", False)), "issues": [str(x) for x in issues], "suggestions": [str(x) for x in suggestions]}
        if last["can_proceed"]:
            break
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Re-check: only block on truly blocking issues; minor improvements must not block."})
    return {"status": "success", "review": last or {"can_proceed": False, "issues": [], "suggestions": []}}
