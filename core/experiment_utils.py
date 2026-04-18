"""Minimal shared helpers for scheme-phase runtime."""
from __future__ import annotations

import re
from pathlib import Path


def sanitize_scheme_markdown_leaks(content: str) -> str:
    """Decode literal ``\\uXXXX`` (six-character) Unicode escapes that models leak into markdown text."""
    if not content:
        return content

    def _repl(m: re.Match[str]) -> str:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return m.group(0)

    return re.sub(r"\\u([0-9a-fA-F]{4})", _repl, content)


def _normalize_artifact_path(path: str) -> str:
    """If path does not start with project/ or artifacts/, treat as artifacts/<name>."""
    if (path or "").startswith("project/") or (path or "").startswith("artifacts/"):
        return path
    return "artifacts/" + path.lstrip("/")


def read_file_under_run(run_root: Path, path: str) -> dict:
    """Read a file under run_root (project/ or artifacts/). Returns {content} or {error}."""
    path = _normalize_artifact_path(path)
    p = (run_root / path).resolve()
    if not p.resolve().is_relative_to(run_root.resolve()) or ".." in path:
        return {"error": "path not under run_root"}
    if not p.is_file():
        return {"error": f"not a file: {path}"}
    return {"content": p.read_text(encoding="utf-8", errors="replace")}


def write_file_under_run(run_root: Path, path: str, content: str) -> dict:
    """Write a file under run_root. Returns {ok, path} or {error}."""
    path = _normalize_artifact_path(path)
    if not path.startswith("project/") and not path.startswith("artifacts/"):
        return {"error": "path must start with project/ or artifacts/"}
    p = (run_root / path).resolve()
    if not p.resolve().is_relative_to(run_root.resolve()) or ".." in path:
        return {"error": "path not under run_root"}
    if path.endswith(".md"):
        content = sanitize_scheme_markdown_leaks(content)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": path}


def output_lang_instruction(lang: str) -> str:
    """One-line instruction for prompts: write all outputs in the given language (zh or en)."""
    if lang == "zh":
        return "\n**Output language:** Write all generated artifacts, review feedback (issues/suggestions), and your replies in **Chinese (Simplified)**."
    return "\n**Output language:** Write all generated artifacts, review feedback (issues/suggestions), and your replies in **English**."

def missing_artifacts_in_dir(
    run_root: Path,
    required_names: tuple[str, ...] | list[str],
    artifact_subdir: str | None = None,
) -> list[str]:
    """Return list of required artifact names that are missing under run_root/artifacts/ (or artifacts/{subdir}/)."""
    art = (run_root / "artifacts" / artifact_subdir) if artifact_subdir else (run_root / "artifacts")
    return [n for n in required_names if not (art / n).is_file()]
