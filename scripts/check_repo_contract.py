from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent


ALLOWED_DOCS_ROOT_FILES = {
    # Existing stable docs (direct children of docs/)
    "README.md",
    "DEVELOPMENT_CONTRACT.md",
    "project_status.md",
    "worklog.md",
}


REQUIRED_MD_SKILL_FRONTMATTER_FIELDS = ("name", "type", "version")
BANNED_IMPORT_SUBSTRINGS = (
    "skills.spine",
    "from skills.spine",
    "import skills.spine",
)
REQUIRED_AGENT_OS_FILES = {
    "AGENTS.md",
    "HEARTBEAT.md",
    "MEMORY.md",
    "SOUL.md",
    "USER.md",
}
ALLOWED_SCRIPT_FILES = {
    "check_repo_contract.py",
    "create_skill_template.py",
    "install_skill.py",
    "list_failure_patterns.py",
    "list_skills.py",
    "run_supervisor_ide.py",
    "run_algo_alpha_phase1.py",
    "run_execution_prep.py",
    "run_ide_execution_agent.py",
    "run_routed_tool.py",
    "run_scheme_agent.py",
    "run_scheme_then_ide.py",
    "scaffold_promotion_record.py",
}


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _load_frontmatter(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if not raw.lstrip().startswith("---"):
        return {}
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end_idx = None
    for i in range(1, min(len(lines), 250)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}
    fm_text = "\n".join(lines[1:end_idx]).strip()
    try:
        data = yaml.safe_load(fm_text) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def check_docs_root() -> list[str]:
    errors: list[str] = []
    docs = REPO_ROOT / "docs"
    if not docs.is_dir():
        return ["docs/ directory missing"]
    for p in sorted(docs.glob("*.md")):
        if p.name not in ALLOWED_DOCS_ROOT_FILES:
            errors.append(
                f"Unexpected top-level doc: docs/{p.name}. "
                f"Move it under docs/agent/, docs/policies/, or docs/skills/, and update docs/README.md."
            )
    return errors


def check_md_skills() -> list[str]:
    errors: list[str] = []
    skills_dir = REPO_ROOT / "docs" / "skills"
    if not skills_dir.exists():
        return errors

    for skill_md in sorted(skills_dir.glob("**/SKILL.md")):
        fm = _load_frontmatter(skill_md)
        missing = [k for k in REQUIRED_MD_SKILL_FRONTMATTER_FIELDS if not str(fm.get(k, "")).strip()]
        if missing:
            rel = skill_md.relative_to(REPO_ROOT).as_posix()
            errors.append(f"MD skill missing frontmatter fields {missing}: {rel}")
            continue
        t = str(fm.get("type")).strip().lower()
        if t not in ("policy", "ops"):
            rel = skill_md.relative_to(REPO_ROOT).as_posix()
            errors.append(f"MD skill frontmatter type must be 'policy' or 'ops': {rel} (got {t!r})")
    return errors


def check_md_skill_registry() -> list[str]:
    errors: list[str] = []
    p = REPO_ROOT / "docs" / "skills" / "manifest.json"
    if not p.exists():
        return errors
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return [f"Invalid JSON: docs/skills/manifest.json ({e})"]
    if not isinstance(data, dict):
        return ["Invalid registry: docs/skills/manifest.json must be a JSON object"]
    sv = str(data.get("schema_version") or "").strip()
    if not sv:
        errors.append("Invalid registry: docs/skills/manifest.json missing schema_version")
    skills = data.get("skills")
    if skills is None:
        return errors
    if not isinstance(skills, list):
        errors.append("Invalid registry: docs/skills/manifest.json skills must be a list")
        return errors
    seen_ids: set[str] = set()
    for i, s in enumerate(skills[:200]):
        if not isinstance(s, dict):
            errors.append(f"Invalid registry entry at skills[{i}]: must be an object")
            continue
        for k in ("id", "type", "version", "path"):
            if not str(s.get(k) or "").strip():
                errors.append(f"Invalid registry entry at skills[{i}]: missing {k}")
        sid = str(s.get("id") or "").strip()
        if sid:
            if sid in seen_ids:
                errors.append(f"Invalid registry: duplicate skill id: {sid}")
            else:
                seen_ids.add(sid)
        # Path must exist and point to a SKILL.md
        rel_path = str(s.get("path") or "").strip()
        if rel_path:
            p_skill = (REPO_ROOT / rel_path).resolve()
            try:
                p_skill.relative_to(REPO_ROOT)
            except Exception:
                errors.append(f"Invalid registry entry at skills[{i}]: path escapes repo_root: {rel_path}")
                continue
            if not p_skill.is_file():
                errors.append(f"Invalid registry entry at skills[{i}]: path not found: {rel_path}")
                continue
            if p_skill.name != "SKILL.md":
                errors.append(f"Invalid registry entry at skills[{i}]: path must point to SKILL.md: {rel_path}")
                continue
            fm = _load_frontmatter(p_skill)
            missing = [k for k in REQUIRED_MD_SKILL_FRONTMATTER_FIELDS if not str(fm.get(k, '')).strip()]
            if missing:
                errors.append(f"Invalid registry entry at skills[{i}]: SKILL.md missing frontmatter {missing}: {rel_path}")
            if str(fm.get("type") or "").strip().lower() not in ("policy", "ops"):
                errors.append(
                    f"Invalid registry entry at skills[{i}]: SKILL.md frontmatter type must be policy|ops: {rel_path}"
                )
        # links (best-effort): repo-local existing paths only
        links = s.get("links") if isinstance(s.get("links"), list) else []
        for link in links[:50]:
            link_s = str(link).strip()
            if not link_s:
                continue
            if "://" in link_s:
                errors.append(f"Invalid registry entry at skills[{i}]: links must be repo-local paths (no URLs): {sid}")
                break
            p_link = (REPO_ROOT / link_s).resolve()
            try:
                p_link.relative_to(REPO_ROOT)
            except Exception:
                errors.append(f"Invalid registry entry at skills[{i}]: link escapes repo_root: {sid} -> {link_s}")
                break
            if not p_link.exists():
                errors.append(f"Invalid registry entry at skills[{i}]: link target missing: {sid} -> {link_s}")
                break
    return errors


def check_agent_os_contracts() -> list[str]:
    """
    Prevent Agent OS drift: docs/agent/ must contain exactly the canonical set.
    """
    errors: list[str] = []
    d = REPO_ROOT / "docs" / "agent"
    if not d.is_dir():
        return ["docs/agent/ directory missing"]
    md = {p.name for p in d.glob("*.md") if p.is_file()}
    missing = sorted(REQUIRED_AGENT_OS_FILES - md)
    extra = sorted(md - REQUIRED_AGENT_OS_FILES)
    if missing:
        errors.append(f"docs/agent/ missing required files: {missing}")
    if extra:
        errors.append(f"docs/agent/ has unexpected files (Agent OS must stay minimal): {extra}")
    return errors


def check_promotion_record_naming() -> list[str]:
    """
    Enforce deterministic naming for promotion decision records.
    """
    errors: list[str] = []
    d = REPO_ROOT / "docs" / "experiments" / "autonomous_research" / "records"
    if not d.exists():
        return errors
    pat = re.compile(r"^\d{8}_[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
    for p in sorted(d.glob("*.md")):
        if p.name == "README.md":
            continue
        if not pat.fullmatch(p.name):
            errors.append(f"Invalid promotion record filename (expected YYYYMMDD_slug.md): {p.relative_to(REPO_ROOT).as_posix()}")
    return errors


def check_scripts_folder() -> list[str]:
    """
    Prevent script sprawl: scripts/ is a small set of thin entrypoints.
    """
    errors: list[str] = []
    d = REPO_ROOT / "scripts"
    if not d.is_dir():
        return ["scripts/ directory missing"]
    py = {p.name for p in d.glob("*.py") if p.is_file()}
    extra = sorted(py - ALLOWED_SCRIPT_FILES)
    if extra:
        errors.append(f"scripts/ has unexpected files (keep entrypoints minimal): {extra}")
    return errors


def check_repo_root_no_stray_python() -> list[str]:
    """
    Repo root should not accumulate one-off python modules.
    Allowed: main.py only.
    """
    errors: list[str] = []
    allowed = {"main.py"}
    py = {p.name for p in REPO_ROOT.glob("*.py") if p.is_file()}
    extra = sorted(py - allowed)
    if extra:
        errors.append(f"Unexpected python files at repo root (move into core/skills/scripts): {extra}")
    return errors


def _iter_markdown_links(md_text: str) -> list[str]:
    # Simple Markdown link extraction: [text](target)
    # Intentionally ignores reference-style links and images; this is a drift guard, not a full parser.
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", md_text or "")


def check_key_markdown_links() -> list[str]:
    """
    Best-effort guardrail: ensure key docs/index pages don't drift by linking to moved/removed files.
    """
    errors: list[str] = []
    key_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "README.md",
        REPO_ROOT / "docs" / "project_status.md",
        REPO_ROOT / "docs" / "DEVELOPMENT_CONTRACT.md",
    ]
    for f in key_files:
        if not f.is_file():
            continue
        raw = f.read_text(encoding="utf-8", errors="replace")
        for link in _iter_markdown_links(raw)[:400]:
            s = str(link).strip()
            if not s:
                continue
            if s.startswith("#") or s.startswith("mailto:"):
                continue
            if "://" in s:
                continue
            # Drop URL fragments and queries.
            s = s.split("#", 1)[0].split("?", 1)[0].strip()
            if not s:
                continue
            # Allow README to reference repo-root files like FFC.md, AI_Investment_Team_Plan.md, etc.
            p = (f.parent / s).resolve()
            try:
                p.relative_to(REPO_ROOT)
            except Exception:
                errors.append(f"Markdown link escapes repo_root: {f.relative_to(REPO_ROOT).as_posix()} -> {link}")
                continue
            if not p.exists():
                errors.append(f"Broken markdown link: {f.relative_to(REPO_ROOT).as_posix()} -> {link}")
    return errors


def check_entrypoints_no_banned_imports() -> list[str]:
    errors: list[str] = []
    entrypoints = [
        REPO_ROOT / "scripts" / "run_scheme_agent.py",
        REPO_ROOT / "scripts" / "run_execution_prep.py",
        REPO_ROOT / "scripts" / "run_routed_tool.py",
        REPO_ROOT / "main.py",
    ]
    for f in entrypoints:
        if not f.is_file():
            continue
        t = f.read_text(encoding="utf-8", errors="replace")
        for bad in BANNED_IMPORT_SUBSTRINGS:
            if bad in t:
                errors.append(f"Banned import reference found: {f.relative_to(REPO_ROOT).as_posix()} contains {bad!r}")
                break
    return errors


def check_quant_soul_policy_skill_sync() -> list[str]:
    """
    Lightweight drift guard:
    ensure quant-soul policy SKILL.md keeps key semantics synchronized
    with canonical docs/policies/quant_soul.md.
    """
    errors: list[str] = []
    p = REPO_ROOT / "docs" / "skills" / "policy" / "quant-soul" / "SKILL.md"
    if not p.is_file():
        return errors
    t = p.read_text(encoding="utf-8", errors="replace").lower()
    required_substrings = (
        "provisional",
        "locked",
        "no universal hard caps",
        "diagnostic_value",
        "threshold",
        "decision",
    )
    missing = [s for s in required_substrings if s not in t]
    if missing:
        errors.append(
            "quant-soul policy skill missing required synced semantics: "
            + ", ".join(missing)
            + " (docs/skills/policy/quant-soul/SKILL.md)"
        )
    return errors


def check_scheme_phase_ops_skill_sync() -> list[str]:
    """
    Lightweight drift guard:
    ensure scheme-phase ops SKILL.md keeps key workflow semantics in sync
    with docs/experiments/scheme_phase/blueprint.md.
    """
    errors: list[str] = []
    p = REPO_ROOT / "docs" / "skills" / "ops" / "scheme-phase" / "SKILL.md"
    if not p.is_file():
        return errors
    t = p.read_text(encoding="utf-8", errors="replace").lower()
    required_substrings = (
        "/artifacts/",
        "exploration protocol",
        "acceptance protocol",
        "provisional",
        "locked",
    )
    missing = [s for s in required_substrings if s not in t]
    if missing:
        errors.append(
            "scheme-phase ops skill missing required synced semantics: "
            + ", ".join(missing)
            + " (docs/skills/ops/scheme-phase/SKILL.md)"
        )
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(check_docs_root())
    errors.extend(check_md_skill_registry())
    errors.extend(check_md_skills())
    errors.extend(check_agent_os_contracts())
    errors.extend(check_promotion_record_naming())
    errors.extend(check_scripts_folder())
    errors.extend(check_repo_root_no_stray_python())
    errors.extend(check_key_markdown_links())
    errors.extend(check_entrypoints_no_banned_imports())
    errors.extend(check_quant_soul_policy_skill_sync())
    errors.extend(check_scheme_phase_ops_skill_sync())

    if errors:
        _eprint("Repo contract check: FAILED\n")
        for e in errors:
            _eprint(f"- {e}")
        _eprint("\nSee docs/DEVELOPMENT_CONTRACT.md for the governing rules.")
        return 1

    print("Repo contract check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

