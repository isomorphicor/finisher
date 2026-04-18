"""Scheme artifact text I/O, JSON helpers, and literature pre-search."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.paper_search import format_papers_for_prompt, search_papers_multi_source
from core.scheme_contract import REQUIRED_SCHEME_ARTIFACTS


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


def _presearch_literature(
    *,
    refined: dict[str, Any] | None,
    fallback_query: str,
) -> str:
    q_parts: list[str] = []
    if refined and refined.get("task_text"):
        q_parts.append(str(refined.get("task_text")))
    if refined and isinstance(refined.get("key_terms"), list):
        kt = [str(x).strip() for x in (refined.get("key_terms") or []) if str(x).strip()]
        if kt:
            q_parts.append(", ".join(kt[:12]))
    q_base = " ".join(q_parts).strip() or fallback_query
    queries = [
        f"{q_base} world model model-based reinforcement learning stochastic control HJB BSDE portfolio",
        f"{q_base} diffusion transformer state space model risk-sensitive control portfolio management",
    ]
    all_hits = []
    for q in queries[:2]:
        hits = search_papers_multi_source(q, limit_per_source=4, timeout=20)
        all_hits.extend(hits)
    block = format_papers_for_prompt(all_hits[:12], max_chars=9000, include_abstract=True).strip()
    return block


def _gather_scheme_package(run_root: Path, max_chars: int = 120000) -> str:
    parts: list[str] = []
    for n in REQUIRED_SCHEME_ARTIFACTS:
        p = run_root / "artifacts" / n
        if p.is_file():
            parts.append(f"--- {n} ---\n{p.read_text(encoding='utf-8', errors='replace')}")
    text = "\n\n".join(parts)
    return (text[:max_chars] + "\n\n[truncated]") if len(text) > max_chars else text
