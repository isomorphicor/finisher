from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class SkillManifestEntry(BaseModel):
    id: str
    version: str
    entry: str
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    trust: str = "project"
    requirements: dict[str, Any] = Field(default_factory=dict)


class SkillRegistryDoc(BaseModel):
    schema_version: str = "skill_registry_v1"
    skills: list[SkillManifestEntry] = Field(default_factory=list)


class SkillRegistry:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.core_dir = self.repo_root / "skills" / "core"
        self.installed_dir = self.repo_root / "skills" / "installed"
        self.registry_path = self.repo_root / "skills" / "registry" / "manifest.json"
        self.core_dir.mkdir(parents=True, exist_ok=True)
        self.installed_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.save(SkillRegistryDoc())

    def load(self) -> SkillRegistryDoc:
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return SkillRegistryDoc(**raw)

    def save(self, doc: SkillRegistryDoc) -> None:
        self.registry_path.write_text(json.dumps(doc.model_dump(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    def upsert(self, entry: SkillManifestEntry) -> None:
        doc = self.load()
        kept = [x for x in doc.skills if x.id != entry.id]
        kept.append(entry)
        doc.skills = sorted(kept, key=lambda x: x.id)
        self.save(doc)

    def discover(self, *, capability: str | None = None, tag: str | None = None) -> list[SkillManifestEntry]:
        doc = self.load()
        out = []
        for s in doc.skills:
            if capability and capability not in s.capabilities:
                continue
            if tag and tag not in s.tags:
                continue
            out.append(s)
        return out

    def install_from_path(self, source_dir: Path) -> dict[str, Any]:
        src = source_dir.resolve()
        manifest_path = src / "skill_manifest.json"
        if not manifest_path.is_file():
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_MANIFEST", "message": "missing skill_manifest.json", "details": {"path": str(src)}}]}
        try:
            entry = SkillManifestEntry(**json.loads(manifest_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValidationError) as e:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_MANIFEST_INVALID", "message": "invalid skill manifest", "details": {"error": str(e)}}]}
        policy_error = _validate_manifest_policy(entry)
        if policy_error is not None:
            return policy_error

        target = self.installed_dir / entry.id
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)
        self.upsert(entry)
        return {"status": "success", "report": {"installed_to": str(target), "skill_id": entry.id, "version": entry.version}}

    def load_callable(self, skill_id: str):
        doc = self.load()
        entry = next((s for s in doc.skills if s.id == skill_id), None)
        if not entry:
            raise KeyError(f"skill not found: {skill_id}")
        repo_root_str = str(self.repo_root)
        if repo_root_str not in sys.path:
            # Ensure dynamically installed project-local skills are importable.
            sys.path.insert(0, repo_root_str)
        module_name, _, attr = entry.entry.partition(":")
        if not module_name or not attr:
            raise ValueError(f"invalid entry: {entry.entry}")
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            # Fallback: load installed skill module by file path.
            parts = module_name.split(".")
            file_candidate = self.installed_dir / skill_id / (parts[-1] + ".py")
            if not file_candidate.is_file():
                raise
            spec = importlib.util.spec_from_file_location(f"installed_{skill_id}_{parts[-1]}", file_candidate)
            if spec is None or spec.loader is None:
                raise
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        fn = getattr(module, attr)
        return fn, entry


def _validate_manifest_policy(entry: SkillManifestEntry) -> dict[str, Any] | None:
    req = entry.requirements or {}
    perms = req.get("permissions") if isinstance(req, dict) else None
    if perms is None:
        return None
    if not isinstance(perms, list):
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_POLICY", "message": "requirements.permissions must be a list", "details": {"skill_id": entry.id}}],
        }
    allowed = {"file", "terminal", "network"}
    unknown = sorted({str(p) for p in perms if str(p) not in allowed})
    if unknown:
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_POLICY", "message": "unknown permission in requirements.permissions", "details": {"unknown": unknown, "allowed": sorted(allowed)}}],
        }
    return None

