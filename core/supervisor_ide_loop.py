"""
Chunked supervisor: optional text-only CIO rounds between ``run_ide_execution_agent`` chunks.

Standalone from ``research_session_pipeline``; entrypoint ``scripts/run_supervisor_ide.py``.
Uses :class:`core.llm.LLMService` — same provider routing as IDE (Ollama, OpenAI via LiteLLM, etc.).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_agent import run_ide_execution_agent
from core.llm import LLMCompletionError, LLMService
from core.scheme_paths import REPO_ROOT, resolve_workspace_root_cli_arg


def _read_if_exists(path: Path, max_chars: int) -> str:
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if len(raw) <= max_chars:
        return raw
    return raw[:max_chars] + "\n\n[TRUNCATED]\n"


def gather_project_context(scheme_session_dir: Path, *, max_chars_per_file: int) -> str:
    """Load capped snippets for CIO (SUBTASKS, review gate, optional WORKLOG)."""
    proj = scheme_session_dir / "project"
    outd = proj / "outputs"
    chunks: list[str] = []
    for label, rel in (
        ("SUBTASKS.md", proj / "SUBTASKS.md"),
        ("REVIEW_GATE.md", outd / "REVIEW_GATE.md"),
        ("review_gate.md", outd / "review_gate.md"),
        ("WORKLOG.md", proj / "WORKLOG.md"),
    ):
        text = _read_if_exists(rel, max_chars_per_file)
        if text.strip():
            chunks.append(f"### {label} (`{rel.name}`)\n\n{text}")
    return "\n\n".join(chunks) if chunks else "(no SUBTASKS/REVIEW_GATE/WORKLOG files found yet)"


def parse_cio_json(raw: str) -> dict[str, Any]:
    """Extract a JSON object from model output (fenced block or first {...})."""
    s = (raw or "").strip()
    if not s:
        return {"continue": True, "next_focus": "", "notes": "empty model output"}
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if m:
        s = m.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    i, depth = None, 0
    for j, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                i = j
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and i is not None:
                try:
                    return json.loads(s[i : j + 1])
                except json.JSONDecodeError:
                    i, depth = None, 0
    return {"continue": True, "next_focus": s[:8000], "notes": "fallback: non-JSON; passed as next_focus"}


CIO_SYSTEM = """You are a research CIO supervisor. You receive capped excerpts from the session \
project (SUBTASKS, review gate, WORKLOG). Reply with **only** a JSON object, no markdown outside JSON, using this schema:
{"continue": true or false, "next_focus": "markdown instructions for the coding agent for the NEXT chunk only", "notes": "one short line for humans"}
Rules:
- Set "continue" to false if the mandate appears complete, or you recommend human handoff, or there is nothing safe to delegate.
- "next_focus" must be actionable (files, commands, acceptance checks). Empty string only if continue is false.
- Do not claim CPCV or production acceptance unless the excerpts clearly show that evidence exists."""


@dataclass
class SupervisorConfig:
    scheme_session_dir: Path
    workspace_root: Path | None
    base_task: str
    cio_model: str
    coder_model: str | None
    max_chunks: int
    chunk_rounds: int
    cio_context_chars: int
    cio_timeout_sec: int
    use_cio: bool
    task_mode: str  # override | supplement
    iteration_mode: bool | None
    exploration_mode: bool | None
    verbose: bool


@dataclass
class SupervisorResult:
    chunks: list[dict[str, Any]] = field(default_factory=list)
    exit_code: int = 0


def run_supervisor_loop(cfg: SupervisorConfig) -> SupervisorResult:
    wr = resolve_workspace_root_cli_arg(str(cfg.workspace_root) if cfg.workspace_root else "")
    session = cfg.scheme_session_dir.resolve()
    out: SupervisorResult = SupervisorResult()
    llm = LLMService()
    outputs = session / "project" / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    for chunk in range(cfg.max_chunks):
        directive: dict[str, Any] = {}
        if cfg.use_cio:
            ctx = gather_project_context(session, max_chars_per_file=cfg.cio_context_chars)
            user_msg = (
                f"Chunk index (0-based): {chunk}\n\n"
                f"--- Project context ---\n{ctx}\n\n"
                f"--- Base task (stable user intent) ---\n{(cfg.base_task or '').strip() or '(none)'}\n"
            )
            if cfg.verbose:
                print(f"[supervisor] CIO round {chunk} (model={cfg.cio_model!r})…", flush=True)
            try:
                msg = llm.chat_completion(
                    [
                        {"role": "system", "content": CIO_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    tools=None,
                    model=cfg.cio_model,
                    temperature=0.2,
                    timeout=cfg.cio_timeout_sec,
                )
                raw = getattr(msg, "content", None) or ""
                if not isinstance(raw, str):
                    raw = str(raw)
                directive = parse_cio_json(raw)
            except LLMCompletionError as e:
                rec = {
                    "chunk": chunk,
                    "phase": "cio",
                    "error": str(e),
                }
                out.chunks.append(rec)
                out.exit_code = 1
                if cfg.verbose:
                    print(f"[supervisor] CIO LLM error: {e}", flush=True)
                break

            (outputs / f"cio_chunk_{chunk:03d}.json").write_text(
                json.dumps(directive, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (outputs / "cio_directive_latest.json").write_text(
                json.dumps(directive, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if not directive.get("continue", True):
                out.chunks.append({"chunk": chunk, "phase": "cio", "directive": directive, "stopped": "cio_continue_false"})
                if cfg.verbose:
                    print("[supervisor] CIO set continue=false — stopping before IDE.", flush=True)
                break

        task = _compose_ide_task(cfg.base_task, directive, chunk)
        if cfg.verbose:
            print(
                f"[supervisor] IDE chunk {chunk} (rounds={cfg.chunk_rounds}, coder_model={cfg.coder_model!r})…",
                flush=True,
            )
        ide = run_ide_execution_agent(
            task=task,
            task_mode=cfg.task_mode,
            scheme_session_dir=session,
            workspace_root=wr,
            model=cfg.coder_model,
            max_rounds=cfg.chunk_rounds,
            verbose=cfg.verbose,
            iteration_mode=cfg.iteration_mode,
            exploration_mode=cfg.exploration_mode,
        )
        rec = {"chunk": chunk, "phase": "ide", "ide_status": ide.get("status"), "directive": directive or None}
        out.chunks.append(rec)
        _append_supervisor_log(outputs, rec)

        st = ide.get("status")
        if st == "success":
            if cfg.verbose:
                print("[supervisor] IDE status success — done.", flush=True)
            break
        if st in ("rejected",) and ide.get("errors"):
            out.exit_code = 1
            if cfg.verbose:
                print(f"[supervisor] IDE rejected: {ide.get('errors')}", flush=True)
            break
    else:
        if cfg.verbose:
            print("[supervisor] max chunks reached.", flush=True)

    if out.exit_code == 0:
        success_any = any(c.get("ide_status") == "success" for c in out.chunks)
        cio_handoff = any(c.get("stopped") == "cio_continue_false" for c in out.chunks)
        if not success_any and not cio_handoff:
            out.exit_code = 1

    (outputs / "supervisor_summary.json").write_text(
        json.dumps(
            {
                "schema_version": "supervisor_ide_chunked_v1",
                "implementation": "core/supervisor_ide_loop.py",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "chunks": out.chunks,
                "exit_code": out.exit_code,
                "repo_root": str(REPO_ROOT),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out


def _compose_ide_task(base_task: str, directive: dict[str, Any], chunk: int) -> str:
    parts: list[str] = []
    bt = (base_task or "").strip()
    if bt:
        parts.append(bt)
    nf = (directive.get("next_focus") or "").strip() if directive else ""
    if nf:
        parts.append(f"### Supervisor directive (chunk {chunk})\n\n{nf}")
    if not parts:
        return "Follow SUBTASKS.md and project/outputs/ review gate; use tools until DONE."
    return "\n\n".join(parts)


def _append_supervisor_log(outputs_dir: Path, record: dict[str, Any]) -> None:
    p = outputs_dir / "supervisor_run.jsonl"
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
