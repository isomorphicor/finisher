"""Structure, keyword-anchor, and topic-alignment gates for scheme sessions."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.experiment_utils import output_lang_instruction
from core.llm import LLMCompletionError, LLMService
from core.quant_gate import run_quant_soul_gate
from core.scheme_contract import (
    ARCHITECTURE_SECTIONS,
    DERIVATION_SECTIONS,
    EXPERIMENT_DESIGN_SECTIONS,
    RESEARCH_PLAN_SECTIONS,
)
from core.scheme_package_io import _gather_scheme_package, _safe_json_loads
from core.scheme_phase_models import get_scheme_phase_default_agent_model
from core.scheme_prompts import TOPIC_ALIGNMENT_SYSTEM


def _section_gate(run_root: Path) -> dict[str, Any]:
    def _read(name: str) -> str:
        p = run_root / "artifacts" / name
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""

    def _has_any_heading(text: str, headings: list[str]) -> bool:
        t = text.lower()
        for h in headings:
            hh = h.lower()
            if re.search(rf"(?m)^\s*#+\s*{re.escape(hh)}\b", t):
                return True
        return False

    def _missing_sections(text: str, required: list[tuple[str, list[str]]]) -> list[str]:
        missing: list[str] = []
        for canonical, variants in required:
            if not _has_any_heading(text, variants):
                missing.append(canonical)
        return missing

    rp = _read("research_plan.md")
    dv = _read("derivation.md")
    ar = _read("architecture_draft.md")
    ed = _read("experiment_design.md")

    research_plan_req = [(x.canonical, list(x.variants)) for x in RESEARCH_PLAN_SECTIONS]
    derivation_req = [(x.canonical, list(x.variants)) for x in DERIVATION_SECTIONS]
    architecture_req = [(x.canonical, list(x.variants)) for x in ARCHITECTURE_SECTIONS]
    experiment_req = [(x.canonical, list(x.variants)) for x in EXPERIMENT_DESIGN_SECTIONS]

    missing_by_file = {
        "research_plan.md": _missing_sections(rp, research_plan_req),
        "derivation.md": _missing_sections(dv, derivation_req),
        "architecture_draft.md": _missing_sections(ar, architecture_req),
        "experiment_design.md": _missing_sections(ed, experiment_req),
    }
    ok = all(not v for v in missing_by_file.values())
    return {"ok": ok, "missing_sections": missing_by_file}


def _tabular_tree_baseline_gate(*, experiment_design: str, quant_related: bool) -> dict[str, Any]:
    """Repo default: tabular GBDT baseline is CatBoost (see docs/reference/quant_tech_stack.md)."""
    if not quant_related:
        return {"ok": True, "must_fix": [], "notes": ["skipped: not quant_related"]}
    ed = (experiment_design or "").lower()
    if "catboost" in ed:
        return {"ok": True, "must_fix": [], "notes": ["CatBoost named in experiment_design"]}
    if re.search(r"\b(lightgbm|lgbm|xgboost|xgb)\b", ed):
        return {
            "ok": False,
            "must_fix": [
                "experiment_design.md: Primary **tabular tree (GBDT) baseline must be CatBoost** "
                "(see `docs/reference/quant_tech_stack.md` → Tabular prior). "
                "Add CatBoost (~300 rounds, defaults) to the experiment matrix. "
                "LightGBM/XGBoost may appear only as optional ablations or when the user explicitly requested them.",
            ],
            "notes": ["LightGBM/XGBoost mentioned without CatBoost"],
        }
    return {"ok": True, "must_fix": [], "notes": ["no competing GBDT library named"]}


def _keyword_anchor_gate(
    *,
    refined: dict[str, Any],
    scheme_text: str,
) -> dict[str, Any]:
    key_terms = refined.get("key_terms") if isinstance(refined.get("key_terms"), list) else []
    key_terms = [str(t).strip() for t in key_terms if str(t).strip()]
    if not key_terms:
        return {"on_topic": True, "hit_count": 0, "min_hits": 0, "missing_terms": [], "present_terms": []}

    hay = (scheme_text or "").lower()
    present: list[str] = []
    missing: list[str] = []
    for t in key_terms[:30]:
        tt = t.lower()
        tt = re.sub(r"\s+", " ", tt).strip()
        if not tt:
            continue
        if tt in hay:
            present.append(t)
        else:
            missing.append(t)

    hit_count = len(present)
    min_hits = max(2, min(8, max(1, len(key_terms) // 6)))
    on_topic = hit_count >= min_hits
    return {
        "on_topic": on_topic,
        "hit_count": hit_count,
        "min_hits": min_hits,
        "present_terms": present,
        "missing_terms": missing[:20],
    }


def _topic_alignment_gate(
    *,
    run_root: Path,
    refined: dict[str, Any],
    models: list[str],
    output_lang: str,
    quant_related: bool,
    verbose: bool = False,
    llm_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Runs deterministic gates first, then optional LLM JSON vote (can be slow; not counted as scheme-agent rounds)."""
    llm = LLMService()
    try:
        llm_timeout = max(30, int(llm_timeout_seconds)) if llm_timeout_seconds is not None else 300
    except (TypeError, ValueError):
        llm_timeout = 300
    lang_inst = output_lang_instruction(output_lang if output_lang in ("zh", "en") else "en")
    if verbose:
        print(
            "  [topic_alignment_gate] loading scheme package + running structure/quant/tabular/keyword checks...",
            flush=True,
        )
    pkg = _gather_scheme_package(run_root, max_chars=120000)
    sec = _section_gate(run_root)
    (run_root / "artifacts" / "structure_gate.json").write_text(json.dumps(sec, ensure_ascii=False, indent=2), encoding="utf-8")
    if not sec.get("ok", True):
        missing_sections = sec.get("missing_sections", {}) if isinstance(sec.get("missing_sections"), dict) else {}
        must_fix = []
        for fname in ("research_plan.md", "derivation.md", "architecture_draft.md", "experiment_design.md"):
            ms = missing_sections.get(fname) if isinstance(missing_sections.get(fname), list) else []
            if ms:
                must_fix.append(f"In {fname}: add missing sections as markdown headings: {', '.join(ms[:10])}.")
        return {
            "on_topic": True,
            "blocking_issues": ["Structure gate failed: required sections are missing; scheme is not executable yet."],
            "must_fix": must_fix[:20],
            "missing_terms": [],
            "notes": [],
        }

    if quant_related:
        q = run_quant_soul_gate(scheme_text=pkg)
        (run_root / "artifacts" / "quant_soul_gate.json").write_text(
            json.dumps({"ok": bool(q.ok), "missing": list(q.missing), "must_fix": list(q.must_fix)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not q.ok:
            return {
                "on_topic": True,
                "blocking_issues": ["Quant soul gate failed: missing hard quant assumptions; scheme is not executable yet."],
                "must_fix": q.must_fix[:20],
                "missing_terms": [],
                "notes": [],
            }

    try:
        ed_only = (run_root / "artifacts" / "experiment_design.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        ed_only = ""
    tbg = _tabular_tree_baseline_gate(experiment_design=ed_only, quant_related=quant_related)
    (run_root / "artifacts" / "tabular_baseline_gate.json").write_text(
        json.dumps(tbg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if quant_related and not tbg.get("ok", True):
        return {
            "on_topic": True,
            "blocking_issues": [
                "Tabular baseline gate failed: experiment_design must name **CatBoost** as the primary GBDT baseline "
                "(repo default; see `docs/reference/quant_tech_stack.md`).",
            ],
            "must_fix": (tbg.get("must_fix") or [])[:20],
            "missing_terms": [],
            "notes": [],
        }

    kw = _keyword_anchor_gate(refined=refined, scheme_text=pkg)
    (run_root / "artifacts" / "topic_anchor_gate.json").write_text(json.dumps(kw, ensure_ascii=False, indent=2), encoding="utf-8")
    if not kw.get("on_topic", True):
        missing_terms = kw.get("missing_terms", [])
        must_fix = [
            "Rewrite the scheme to match the refined task exactly (do not change the problem).",
            "In research_plan.md: update Problem Statement, Success Criteria, and Constraints to match the refined task exactly.",
            "In derivation.md: align Notation/Assumptions/Objective with the refined task (no generic substitutes).",
            "In architecture_draft.md: ensure modules/data flow are for this task (not a neighboring topic).",
            "In experiment_design.md: ensure experiments test the refined hypotheses/variables/metrics for this task.",
        ]
        if missing_terms:
            must_fix.append("Explicitly include these missing key terms where appropriate (especially in research_plan.md and experiment_design.md): " + ", ".join(missing_terms[:12]))
        return {
            "on_topic": False,
            "blocking_issues": ["Keyword anchor check failed: too few refined key terms appear in the scheme package."],
            "must_fix": must_fix,
            "missing_terms": missing_terms,
            "notes": [],
        }
    user = json.dumps({"refined_task": refined, "scheme_package": pkg}, ensure_ascii=False)
    chosen_models = [m.strip() for m in (models or []) if m and str(m).strip()]
    if not chosen_models:
        chosen_models = [get_scheme_phase_default_agent_model()]

    outputs: list[dict[str, Any]] = []
    vote_models = chosen_models[:3]
    for vi, m in enumerate(vote_models):
        if verbose:
            print(
                f"  [topic_alignment_gate] LLM vote {vi + 1}/{len(vote_models)}: {m} (timeout {llm_timeout}s, large context)...",
                flush=True,
            )
        try:
            msg = llm.chat_completion(
                messages=[
                    {"role": "system", "content": TOPIC_ALIGNMENT_SYSTEM + lang_inst},
                    {"role": "user", "content": user},
                ],
                model=m,
                temperature=0.2,
                response_format={"type": "json_object"},
                timeout=llm_timeout,
            )
            raw_m = (getattr(msg, "content", None) or "").strip()
        except LLMCompletionError:
            raw_m = ""
        data = _safe_json_loads(raw_m) or {}
        outputs.append({"model": m, "data": data})

    votes_true = 0
    votes_false = 0
    blocking_issues: list[str] = []
    must_fix: list[str] = []
    missing_terms: list[str] = []
    notes: list[str] = []

    def _add_unique(dst: list[str], items: list[Any], cap: int) -> None:
        for x in items:
            s = str(x).strip()
            if not s:
                continue
            if s not in dst:
                dst.append(s)
            if len(dst) >= cap:
                break

    for o in outputs:
        d = o.get("data") if isinstance(o.get("data"), dict) else {}
        if bool(d.get("on_topic", False)):
            votes_true += 1
        else:
            votes_false += 1
        _add_unique(blocking_issues, d.get("blocking_issues") if isinstance(d.get("blocking_issues"), list) else [], 24)
        _add_unique(must_fix, d.get("must_fix") if isinstance(d.get("must_fix"), list) else [], 24)
        _add_unique(missing_terms, d.get("missing_terms") if isinstance(d.get("missing_terms"), list) else [], 30)
        _add_unique(notes, d.get("notes") if isinstance(d.get("notes"), list) else [], 20)

    on_topic = votes_false <= votes_true
    return {
        "on_topic": on_topic,
        "blocking_issues": blocking_issues[:20],
        "must_fix": must_fix[:20],
        "missing_terms": missing_terms[:20],
        "notes": notes[:20],
    }
