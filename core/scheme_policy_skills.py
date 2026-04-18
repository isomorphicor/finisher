"""Quant policy text, task ideation, and MD policy skill injections for the scheme agent."""
from __future__ import annotations

import json
import re
from typing import Any

from core.llm import LLMCompletionError, LLMService
from core.scheme_paths import REPO_ROOT


def _load_quant_soul_text(max_chars: int = 7000) -> str:
    p = REPO_ROOT / "docs" / "policies" / "quant_soul.md"
    if not p.exists():
        return ""
    try:
        t = p.read_text(encoding="utf-8", errors="replace").strip()
        if len(t) > max_chars:
            t = t[:max_chars].rstrip() + "\n\n[TRUNCATED]"
        return t
    except Exception:
        return ""


def _ideate_quant_task(*, llm: LLMService, model: str, timeout: int = 120) -> str:
    """
    When the user provides no concrete topic, propose a bounded quant research task.
    This is intentionally lightweight: it returns one task string and records it as an artifact.
    """
    quant_soul = _load_quant_soul_text(max_chars=6000)
    system = (
        "You are the CIO of a quant research agent.\n"
        "Your job: propose ONE research task the team can execute end-to-end (scheme artifacts only).\n"
        "Constraints:\n"
        "- Must be quant-investing research (alpha / risk / portfolio / execution / data quality).\n"
        "- Must be narrow, testable, and doable with a small evidence plan.\n"
        "- Avoid requiring proprietary data or web scraping as a hard dependency.\n"
        "- Output ONLY the task text (no bullets, no preamble).\n"
    )
    user = "Quant hard gates (must not violate; use as safety/quality constraints):\n\n" + (quant_soul or "(none)")
    try:
        msg = llm.chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=model,
            temperature=0.4,
            timeout=timeout,
        )
        t = (getattr(msg, "content", "") or "").strip()
    except LLMCompletionError:
        t = ""
    t = re.sub(r"^([\"'`]+)|([\"'`]+)$", "", t).strip()
    return t or "Propose and validate a simple baseline factor model for cross-sectional stock returns with strict time-safety gates."


def _load_md_skill_registry() -> dict[str, Any]:
    """
    Load docs/skills/manifest.json (MD skills registry).
    Fail-closed to empty on any error (registry is optional, fallback behavior exists).
    """
    p = REPO_ROOT / "docs" / "skills" / "manifest.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_policy_skill_injections(*, task_text: str, quant_related: bool, max_total_chars: int = 12000) -> list[str]:
    """
    Load policy MD skills from docs/skills/manifest.json and return prompt injection blocks.
    Minimal trigger logic by design:
    - if quant_related: include any policy skill whose triggers match (or is the quant-soul skill)
    - otherwise: include policy skills whose triggers match the task text
    """
    reg = _load_md_skill_registry()
    skills = reg.get("skills") if isinstance(reg.get("skills"), list) else []
    if not skills:
        return []

    t = (task_text or "").lower()
    out: list[str] = []
    used = 0

    def _match_triggers(triggers: list[str]) -> bool:
        if not triggers:
            return False
        return any(str(x).strip().lower() in t for x in triggers if str(x).strip())

    for s in skills:
        if not isinstance(s, dict):
            continue
        if str(s.get("type") or "").strip().lower() != "policy":
            continue
        applies_to = s.get("applies_to") if isinstance(s.get("applies_to"), list) else []
        applies_to_norm = {str(x).strip().lower() for x in applies_to if str(x).strip()}
        if applies_to_norm and ("all" not in applies_to_norm) and ("scheme_agent" not in applies_to_norm):
            continue

        triggers = s.get("triggers") if isinstance(s.get("triggers"), list) else []
        triggers_norm = [str(x).strip() for x in triggers if str(x).strip()]

        sid = str(s.get("id") or "").strip()
        if quant_related:
            if (sid != "policy.quant-soul") and (not _match_triggers(triggers_norm)):
                continue
        else:
            if not _match_triggers(triggers_norm):
                continue

        rel_path = str(s.get("path") or "").strip()
        if not rel_path:
            continue
        skill_path = (REPO_ROOT / rel_path).resolve()
        try:
            txt = skill_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            continue

        name = str(s.get("name") or sid or "policy").strip() or "policy"
        version = str(s.get("version") or "").strip()

        block_parts: list[str] = []
        block_parts.append(f"[MD Policy Skill] {name}" + (f" v{version}" if version else ""))
        links = s.get("links") if isinstance(s.get("links"), list) else []
        links_norm = [str(x).strip() for x in links if str(x).strip()]
        if links_norm:
            block_parts.append("Links:\n" + "\n".join(f"- {x}" for x in links_norm[:10]))
        skill_txt = txt
        if len(skill_txt) > 6000:
            skill_txt = skill_txt[:6000].rstrip() + "\n\n[TRUNCATED]"
        block_parts.append("SKILL.md:\n" + skill_txt)

        block = "\n\n".join(block_parts).strip()
        if not block:
            continue
        if used + len(block) > max_total_chars:
            break
        out.append(block)
        used += len(block)

    return out


def _looks_quant_related(text: str) -> bool:
    t = (text or "").lower()
    if not t:
        return False
    keywords = [
        "quant",
        "alpha",
        "factor",
        "portfolio",
        "trading",
        "backtest",
        "walk-forward",
        "walk forward",
        "returns",
        "risk",
        "sharpe",
        "drawdown",
        "transaction cost",
        "slippage",
        "investment",
        "asset management",
        "world model",
    ]
    return any(k in t for k in keywords)
