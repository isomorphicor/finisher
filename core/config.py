from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env", override=False)


class PathsConfig(BaseModel):
    """Mirrors ``paths`` in ``config/settings.yaml`` (orchestration roots, not secrets)."""

    model_config = ConfigDict(extra="ignore")
    data_dir: Optional[str] = None
    runs_dir: Optional[str] = None  # default INVERST_SCHEME_PHASE_RUNS; consumed in core.scheme_paths
    workspace_root: Optional[str] = None  # default IDE/prep root when CLI omits --workspace-root; see core.scheme_paths
    skills_dir: str = "skills"
    logs_dir: str = "logs"
    processed_dir: str = "data/processed"


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    provider: str = "openai"
    default_model: str = "gpt-4o"
    timeout: int = 60
    max_retries: int = 3
    openai: dict[str, Any] = {}
    ollama: dict[str, Any] = {}
    mlx: dict[str, Any] = {}  # optional: model_id, fallback_for_tools (e.g. "ollama")

class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = "finisher"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

def _resolve_settings_yaml_path(config_path: str | None) -> Path | None:
    """
    Resolve ``config/settings.yaml``: explicit path first, then **repo root** (stable), then cwd.
    Avoids silently falling back to ``provider: openai`` when cwd is not the repo.
    """
    repo_root = REPO_ROOT
    candidates: list[Path] = []
    if config_path and str(config_path).strip():
        p = Path(config_path)
        candidates.append(p if p.is_absolute() else Path.cwd() / p)
    candidates.append(repo_root / "config" / "settings.yaml")
    candidates.append(Path.cwd() / "config" / "settings.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return None


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    app: AppConfig = Field(default_factory=AppConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)

    @classmethod
    def load(cls, config_path: str | None = None) -> "Settings":
        """Load settings from YAML. Default: ``<repo>/config/settings.yaml`` regardless of cwd."""
        path = _resolve_settings_yaml_path(config_path)
        if path is None:
            return cls(
                app=AppConfig(),
                llm=LLMConfig(),
                paths=PathsConfig(),
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        # Be permissive: ignore unknown top-level keys to keep config stable while slimming code.
        return cls(**data)

# Global Instance
settings = Settings.load()
