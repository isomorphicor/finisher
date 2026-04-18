"""Scheme-phase LLM model resolution from ``config/agents.yaml`` and env."""
from __future__ import annotations

import os
from typing import Any

import yaml

from core.scheme_paths import REPO_ROOT


def _load_scheme_phase_hiring_config() -> dict[str, Any]:
    cfg_path = REPO_ROOT / "config" / "agents.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return data.get("scheme_phase") if isinstance(data, dict) else {}
    except Exception:
        return {}


def _pick_reviewer_model(cfg: dict[str, Any]) -> str | None:
    env = (os.environ.get("INVERST_SCHEME_REVIEWER_MODEL") or "").strip()
    if env:
        return env
    reviewers = cfg.get("reviewers") if isinstance(cfg.get("reviewers"), list) else []
    for r in reviewers:
        if isinstance(r, dict) and (r.get("model") or "").strip():
            return str(r.get("model")).strip()
    return None


def _pick_reviewer_models(cfg: dict[str, Any]) -> list[str]:
    env = (os.environ.get("INVERST_SCHEME_REVIEWER_MODELS") or "").strip()
    if env:
        return [x.strip() for x in env.split(",") if x.strip()]
    out: list[str] = []
    reviewers = cfg.get("reviewers") if isinstance(cfg.get("reviewers"), list) else []
    for r in reviewers:
        if isinstance(r, dict) and (r.get("model") or "").strip():
            out.append(str(r.get("model")).strip())
    return out


def _pick_translator_model(cfg: dict[str, Any]) -> str | None:
    env = (os.environ.get("INVERST_SCHEME_TRANSLATOR_MODEL") or "").strip()
    if env:
        return env
    tr = cfg.get("translator") if isinstance(cfg.get("translator"), dict) else {}
    m = (tr.get("model") or "").strip() if isinstance(tr, dict) else ""
    return m or None


def get_scheme_phase_default_agent_model() -> str:
    """
    Single source for the scheme agent's primary model name.
    Precedence: env INVERST_SCHEME_AGENT_MODEL → config agents.yaml scheme_phase.default_agent_model
    → first scheme_phase.reviewers[].model → last-resort string.
    """
    env = (os.environ.get("INVERST_SCHEME_AGENT_MODEL") or "").strip()
    if env:
        return env
    cfg = _load_scheme_phase_hiring_config()
    if isinstance(cfg, dict):
        raw = (cfg.get("default_agent_model") or "").strip()
        if raw:
            return raw
        rm = _pick_reviewer_model(cfg)
        if rm:
            return rm
    return "nemotron-3-super:latest"
