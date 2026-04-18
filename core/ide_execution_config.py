"""IDE execution and supervisor CIO settings from ``config/agents.yaml`` and env (``core/ide_agent.py``, ``run_supervisor_ide``)."""
from __future__ import annotations

import os
from typing import Any

import yaml

from core.scheme_paths import REPO_ROOT
from core.scheme_phase_models import get_scheme_phase_default_agent_model


def _load_agents_yaml() -> dict[str, Any]:
    """Full ``config/agents.yaml`` root object (ide_execution, scheme_phase, agents, supervisor, …)."""
    cfg_path = REPO_ROOT / "config" / "agents.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_ide_execution_config() -> dict[str, Any]:
    data = _load_agents_yaml()
    ie = data.get("ide_execution")
    return ie if isinstance(ie, dict) else {}


def get_ide_execution_int(key: str, env_var: str, default: int) -> int:
    """
    IDE execution numeric setting: env ``env_var`` wins, else ``agents.yaml`` ``ide_execution.<key>``, else ``default``.
    """
    raw = (os.environ.get(env_var) or "").strip()
    if raw:
        try:
            return max(0, int(raw, 10))
        except ValueError:
            pass
    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        v = cfg.get(key)
        if v is not None:
            try:
                return max(0, int(v))
            except (TypeError, ValueError):
                pass
    return default


def get_ide_execution_skills_mode() -> str:
    """
    ``compact`` | ``full`` | other — controls SKILL.md embedding in the IDE system prompt.
    Env ``INVERST_IDE_SKILLS`` overrides ``agents.yaml`` ``ide_execution.skills_inject``.
    """
    raw = (os.environ.get("INVERST_IDE_SKILLS") or "").strip()
    if raw:
        return raw.lower()
    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        s = cfg.get("skills_inject") or cfg.get("ide_skills_inject")
        if s is not None and str(s).strip():
            return str(s).strip().lower()
    return "compact"


def resolve_ide_execution_model(cli_model: str | None = None) -> tuple[str, str]:
    """
    Resolved model for ``run_ide_execution_agent`` and LLM routing.

    Returns ``(model_name, source_tag)``. Precedence:

    1. Non-empty ``cli_model`` (e.g. ``run_ide_execution_agent(..., model=...)`` / CLI ``--model``)
    2. ``INVERST_CODER_MODEL``
    3. ``INVERST_IDE_EXEC_AGENT_MODEL`` (legacy alias)
    4. ``config/agents.yaml`` → ``ide_execution.coder_model``
    5. Fallback: ``get_scheme_phase_default_agent_model()`` (scheme phase default — **not** ideal for IDE; keep ``coder_model`` set)

    ``agents.yaml`` is read from the repo root (``REPO_ROOT / config/agents.yaml``), not cwd.
    """
    if cli_model is not None and str(cli_model).strip():
        return str(cli_model).strip(), "cli"
    env_coder = (os.environ.get("INVERST_CODER_MODEL") or "").strip()
    if env_coder:
        return env_coder, "env_INVERST_CODER_MODEL"
    env_legacy = (os.environ.get("INVERST_IDE_EXEC_AGENT_MODEL") or "").strip()
    if env_legacy:
        return env_legacy, "env_INVERST_IDE_EXEC_AGENT_MODEL"
    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        raw = (cfg.get("coder_model") or "").strip()
        if raw:
            return raw, "agents_yaml_ide_execution.coder_model"
    fb = get_scheme_phase_default_agent_model()
    return fb, "fallback_scheme_phase_default_agent_model"


def resolve_supervisor_cio_model(cli_model: str | None = None) -> tuple[str, str]:
    """
    Model for chunked supervisor **CIO** rounds (text-only JSON; no tools).

    Returns ``(model_name, source_tag)``. Precedence:

    1. Non-empty ``cli_model`` (``--cio-model`` on ``run_supervisor_ide.py``)
    2. ``INVERST_CIO_MODEL``
    3. ``config/agents.yaml`` → ``supervisor.cio_model``
    4. ``config/agents.yaml`` → ``agents.cio.model`` (persona block)
    5. ``config/settings.yaml`` → ``llm.default_model`` (same routing as :class:`core.llm.LLMService`)
    6. Fallback: ``get_scheme_phase_default_agent_model()``

    Switching provider (Ollama vs OpenAI vs …) is done via ``settings.llm.provider`` and model ids; this resolver only picks the **model id string**.
    """
    if cli_model is not None and str(cli_model).strip():
        return str(cli_model).strip(), "cli"
    env_cio = (os.environ.get("INVERST_CIO_MODEL") or "").strip()
    if env_cio:
        return env_cio, "env_INVERST_CIO_MODEL"
    root = _load_agents_yaml()
    sup = root.get("supervisor")
    if isinstance(sup, dict):
        raw = (sup.get("cio_model") or "").strip()
        if raw:
            return raw, "agents_yaml_supervisor.cio_model"
    agents = root.get("agents")
    if isinstance(agents, dict):
        cio = agents.get("cio")
        if isinstance(cio, dict):
            raw = (str(cio.get("model") or "")).strip()
            if raw:
                return raw, "agents_yaml_agents.cio.model"
    from core.config import settings

    dm = (settings.llm.default_model or "").strip()
    if dm:
        return dm, "settings_llm.default_model"
    fb = get_scheme_phase_default_agent_model()
    return fb, "fallback_scheme_phase_default_agent_model"


def get_ide_execution_coder_model() -> str:
    """Same resolution as :func:`resolve_ide_execution_model` without CLI; returns model name only."""
    m, _ = resolve_ide_execution_model(None)
    return m


def get_ide_execution_translate_task_enabled() -> bool:
    """
    Whether to translate non-English ``--task`` / Override text to English before the first IDE user message.

    Env ``INVERST_IDE_TRANSLATE_TASK`` wins: ``0`` / ``false`` / ``no`` / ``off`` = disabled;
    ``1`` / ``true`` / ``yes`` / ``on`` = enabled.
    Else ``config/agents.yaml`` → ``ide_execution.translate_task_to_english`` (default **True**).
    """
    raw = (os.environ.get("INVERST_IDE_TRANSLATE_TASK") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        v = cfg.get("translate_task_to_english")
        if v is not None:
            if isinstance(v, bool):
                return v
            s = str(v).strip().lower()
            if s in ("0", "false", "no", "off"):
                return False
            if s in ("1", "true", "yes", "on"):
                return True
    return True


def get_ide_execution_ide_rules_profile() -> str:
    """
    Which IDE rules bundle is embedded in the system prompt.

    - ``core`` (default): ``docs/reference/ide_core_rules.md`` only (+ short intro/loop in code).
    - ``extended``: core **plus** truncated ``docs/reference/ide_execution_rules.md``.

    Env ``INVERST_IDE_RULES_PROFILE`` wins (``core`` / ``extended``);
    else ``config/agents.yaml`` → ``ide_execution.ide_rules_profile``.
    """
    raw = (os.environ.get("INVERST_IDE_RULES_PROFILE") or "").strip().lower()
    if raw in ("core", "extended"):
        return raw
    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        s = (cfg.get("ide_rules_profile") or "").strip().lower()
        if s in ("core", "extended"):
            return s
    return "core"


def resolve_ide_execution_task_translate_model(coder_model: str) -> str:
    """
    Model used only for ``--task`` → English translation.

    Optional ``ide_execution.task_translate_model`` in ``agents.yaml``; if empty, uses ``coder_model``.
    """
    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        tm = (cfg.get("task_translate_model") or "").strip()
        if tm:
            return tm
    return coder_model


def get_ide_execution_command_allowlist() -> tuple[str, ...]:
    """
    Allowlisted command base tokens for IDE ``terminal_run``.

    Precedence:
    1. Env ``INVERST_IDE_COMMAND_ALLOWLIST`` (comma-separated, e.g. ``python,pytest,rg``)
    2. ``config/agents.yaml`` → ``ide_execution.command_allowlist`` (YAML list or comma-separated string)
    3. Built-in safe default set
    """
    default = (
        "python",
        "python3",
        "pytest",
        "git",
        "make",
        "ls",
        "pwd",
        "echo",
        "env",
        "cd",
        "rg",
        "cat",
        "sed",
        "awk",
        "bash",
        "sh",
    )

    def _parse_csv(raw: str) -> tuple[str, ...]:
        vals = [x.strip() for x in raw.split(",")]
        out = tuple(x for x in vals if x)
        return out

    env_raw = (os.environ.get("INVERST_IDE_COMMAND_ALLOWLIST") or "").strip()
    if env_raw:
        parsed = _parse_csv(env_raw)
        return parsed or default

    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        val = cfg.get("command_allowlist")
        if isinstance(val, list):
            out = tuple(str(x).strip() for x in val if str(x).strip())
            if out:
                return out
        if isinstance(val, str) and val.strip():
            parsed = _parse_csv(val)
            if parsed:
                return parsed
    return default


def get_ide_execution_write_scope() -> str:
    """
    Write scope for IDE execution tools.

    - ``project`` (default): ``<session>/project/**``
    - ``session``: ``<session>/**``
    - ``repo``: full Inverst checkout when ``workspace_root`` is the repo root; if workspace is a
      parent directory (expanded for scheme sessions), ``repo`` is narrowed to session ``project/``
      (see ``skills.ide_execution.build_allowed_write_prefixes``).

    Env ``INVERST_IDE_WRITE_SCOPE`` wins, then ``agents.yaml`` ``ide_execution.write_scope``.
    """
    allowed = {"project", "session", "repo"}
    env_raw = (os.environ.get("INVERST_IDE_WRITE_SCOPE") or "").strip().lower()
    if env_raw in allowed:
        return env_raw
    cfg = _load_ide_execution_config()
    if isinstance(cfg, dict):
        raw = str(cfg.get("write_scope") or "").strip().lower()
        if raw in allowed:
            return raw
    return "project"
