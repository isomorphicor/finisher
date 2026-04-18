from __future__ import annotations

import json
import re
from typing import Any

from core.llm import LLMCompletionError, LLMService


REFINE_USER_NEED_SYSTEM = """You are a research task refiner.

Input: a raw user need (often fuzzy, incomplete, multi-threaded).
Output: a structured task spec that can be used as the single source of truth for downstream scheme design.

Return ONLY one JSON object with these keys:
- task_text: string (the refined task, self-contained)
- objectives: array of strings (must be measurable / checkable)
- non_goals: array of strings (explicitly out of scope)
- constraints: array of strings (data constraints, time-safety constraints, compute constraints, etc.)
- deliverables: array of strings (must include the 4 scheme artifacts)
- key_terms: array of strings (topic anchors; 5-20 short terms/phrases)
- suggest_literature_search: boolean

Rules:
- Do not invent private data or user resources.
- Be specific enough that an agent cannot drift to a different topic.
- Keep task_text concise but unambiguous.
- **Data paths:** Copy every user-provided absolute file path and every `*.ftr` / `*.csv` / `*.parquet` path verbatim into `task_text` or `constraints`. Do not paraphrase or drop them; downstream scheme artifacts must cite the same paths.
"""


def extract_data_path_anchors(raw_need: str) -> list[str]:
    """Collect dataset paths from raw user text (absolute paths, backticks)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in re.finditer(r"(/[^\s`'\"]+?\.(?:ftr|csv|parquet|feather))", raw_need):
        s = m.group(1).rstrip(".,;)")
        if s not in seen:
            seen.add(s)
            out.append(s)
    for m in re.finditer(r"`([^`]+)`", raw_need):
        inner = m.group(1).strip()
        if len(inner) < 5:
            continue
        if "/" in inner or inner.endswith((".ftr", ".csv", ".parquet", ".feather")):
            if inner not in seen:
                seen.add(inner)
                out.append(inner)
    for tok in raw_need.split():
        t = tok.strip(".,;:()[]{}`'\"")
        if len(t) < 8:
            continue
        if "/" in t and t.endswith((".ftr", ".csv", ".parquet", ".feather")):
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out[:24]


def merge_data_path_anchors_into_refined(*, raw_need: str, refined: dict[str, Any]) -> dict[str, Any]:
    """If the LLM omitted dataset paths from task_text, append them so anchors are never dropped."""
    out = dict(refined)
    tt = str(out.get("task_text") or "").strip()
    anchors = extract_data_path_anchors(raw_need)
    missing = [a for a in anchors if a and a not in tt]
    if not missing:
        return out
    block = "\n\nData paths (verbatim; do not omit in scheme artifacts):\n" + "\n".join(f"- {a}" for a in missing)
    out["task_text"] = tt + block
    cons = list(out.get("constraints") or [])
    if not isinstance(cons, list):
        cons = []
    for a in missing:
        line = f"Use data file at this path (verbatim): {a}"
        if not any(a in str(c) for c in cons):
            cons.append(line)
    out["constraints"] = cons
    kt = list(out.get("key_terms") or [])
    if not isinstance(kt, list):
        kt = []
    for a in missing:
        base = a.split("/")[-1]
        if base and base not in kt:
            kt.append(base)
    out["key_terms"] = kt[:30]
    return out


def _safe_json_loads(s: str) -> dict[str, Any] | None:
    raw = (s or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw[3:]
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip().rsplit("```", 1)[0].strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def refine_user_need_to_task(
    *,
    raw_need: str,
    model: str,
    output_lang: str = "en",
) -> dict[str, Any]:
    llm = LLMService()
    lang_line = "Write all strings in Chinese (Simplified)." if output_lang == "zh" else "Write all strings in English."
    try:
        msg = llm.chat_completion(
            messages=[
                {"role": "system", "content": REFINE_USER_NEED_SYSTEM + "\n\n" + lang_line},
                {"role": "user", "content": raw_need},
            ],
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = (getattr(msg, "content", None) or "").strip()
    except LLMCompletionError:
        raw = ""
    data = _safe_json_loads(raw) or {}

    def _as_list(x: Any) -> list[str]:
        if isinstance(x, list):
            return [str(i).strip() for i in x if str(i).strip()]
        return []

    refined = {
        "task_text": str(data.get("task_text") or "").strip(),
        "objectives": _as_list(data.get("objectives")),
        "non_goals": _as_list(data.get("non_goals")),
        "constraints": _as_list(data.get("constraints")),
        "deliverables": _as_list(data.get("deliverables")),
        "key_terms": _as_list(data.get("key_terms")),
        "suggest_literature_search": bool(data.get("suggest_literature_search", False)),
    }

    if not refined["deliverables"]:
        refined["deliverables"] = [
            "research_plan.md",
            "derivation.md",
            "architecture_draft.md",
            "experiment_design.md",
        ]
    refined = merge_data_path_anchors_into_refined(raw_need=raw_need, refined=refined)
    return refined

