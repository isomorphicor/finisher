from __future__ import annotations

import json
import re
from typing import Any

from core.llm import LLMCompletionError, LLMService


TRANSLATE_SYSTEM = """You are a translation engine.

Return ONLY one JSON object: {"translation": "..."}.

Rules:
- Preserve markdown structure (headings, lists, tables) as much as possible.
- Do NOT translate or edit placeholder tokens that look like <<<CODE_BLOCK_0>>> or <<<INLINE_CODE_0>>>. Keep them unchanged.
- Do not add explanations.
"""


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


def _looks_english(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    letters = len(re.findall(r"[A-Za-z]", t))
    non_ascii = len(re.findall(r"[^\x00-\x7F]", t))
    return letters >= max(20, non_ascii * 3)


def _mask_code_spans(text: str) -> tuple[str, dict[str, str]]:
    t = text or ""
    repl: dict[str, str] = {}

    def _put(prefix: str, idx: int, original: str) -> str:
        key = f"<<<{prefix}_{idx}>>>"
        repl[key] = original
        return key

    fenced_pat = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    fenced = list(fenced_pat.finditer(t))
    if fenced:
        out_parts: list[str] = []
        last = 0
        for i, m in enumerate(fenced):
            out_parts.append(t[last:m.start()])
            out_parts.append(_put("CODE_BLOCK", i, m.group(0)))
            last = m.end()
        out_parts.append(t[last:])
        t = "".join(out_parts)

    inline_pat = re.compile(r"`[^`\n]+`")
    inline = list(inline_pat.finditer(t))
    if inline:
        out_parts = []
        last = 0
        base = len([k for k in repl if k.startswith("<<<INLINE_CODE_")])
        for j, m in enumerate(inline):
            out_parts.append(t[last:m.start()])
            out_parts.append(_put("INLINE_CODE", base + j, m.group(0)))
            last = m.end()
        out_parts.append(t[last:])
        t = "".join(out_parts)

    return t, repl


def _unmask_code_spans(text: str, repl: dict[str, str]) -> str:
    out = text or ""
    for key, original in repl.items():
        out = out.replace(key, original)
    return out


def translate_text(
    *,
    text: str,
    target_lang: str,
    model: str,
) -> str:
    masked_text, repl = _mask_code_spans(text)
    llm = LLMService()
    if target_lang == "en":
        lang_line = "Translate the user content into English."
    elif target_lang == "zh":
        lang_line = "Translate the user content into Simplified Chinese."
    else:
        lang_line = f"Translate the user content into {target_lang}."

    try:
        msg = llm.chat_completion(
            messages=[
                {"role": "system", "content": TRANSLATE_SYSTEM + "\n\n" + lang_line},
                {"role": "user", "content": masked_text},
            ],
            model=model,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw_t = (getattr(msg, "content", None) or "").strip()
    except LLMCompletionError:
        raw_t = ""
    data = _safe_json_loads(raw_t) or {}
    out = str(data.get("translation") or "").strip()
    if not out:
        return ""
    return _unmask_code_spans(out, repl).strip()


def translate_to_english_if_needed(*, text: str, model: str) -> str:
    if _looks_english(text):
        return text
    out = translate_text(text=text, target_lang="en", model=model)
    return out or text
