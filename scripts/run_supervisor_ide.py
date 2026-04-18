#!/usr/bin/env python3
"""
Chunked **supervisor** + IDE execution (standalone; not ``research_session_pipeline``).

- **CIO** = text-only JSON plan (reads capped ``SUBTASKS.md``, ``outputs/REVIEW_GATE.md`` / ``review_gate.md``, ``WORKLOG.md``).
- **IDE** = repeated ``run_ide_execution_agent`` with ``--chunk-rounds`` per subprocess.

Routing uses the same stack as the rest of the repo: ``config/settings.yaml`` ``llm.provider`` (e.g. ``ollama`` for cheap local experiments, ``openai`` for APIs) and model ids from CLI / env / ``config/agents.yaml`` (see ``resolve_supervisor_cio_model`` in ``core/ide_execution_config.py``).

Example (local Ollama)::

  python scripts/run_supervisor_ide.py out/algo_alpha/main \\
    --base-task "Continue from SUBTASKS; finish open items." \\
    --max-chunks 4 --chunk-rounds 60

Example (override CIO model only)::

  INVERST_CIO_MODEL=gpt-4o-mini python scripts/run_supervisor_ide.py out/algo_alpha/main --base-task "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.config import settings
from core.ide_execution_config import resolve_supervisor_cio_model
from core.supervisor_ide_loop import SupervisorConfig, run_supervisor_loop


def main() -> None:
    p = argparse.ArgumentParser(description="Chunked supervisor + IDE (provider-agnostic via LLMService)")
    p.add_argument(
        "scheme_session_dir",
        help="Session dir with project/ (e.g. out/<project>/<session>)",
    )
    p.add_argument("--workspace-root", default="", help="IDE workspace root; default from config")
    p.add_argument(
        "--base-task",
        default="",
        help="Stable user intent prepended each chunk (combined with CIO next_focus).",
    )
    p.add_argument(
        "--cio-model",
        default="",
        help="CIO model id; default from resolve_supervisor_cio_model (CLI > INVERST_CIO_MODEL > agents.yaml supervisor.cio_model > agents.cio.model > settings llm.default_model).",
    )
    p.add_argument(
        "--coder-model",
        default="",
        help="IDE coder model; default same as run_ide_execution_agent (ide_execution / env).",
    )
    p.add_argument("--max-chunks", type=int, default=5, help="Max supervisor iterations (CIO + IDE)")
    p.add_argument("--chunk-rounds", type=int, default=48, help="max_rounds per IDE subprocess")
    p.add_argument("--cio-context-chars", type=int, default=12000, help="Max chars per context file for CIO")
    p.add_argument("--cio-timeout", type=int, default=180, help="LLM timeout seconds for CIO only")
    p.add_argument("--no-cio", action="store_true", help="Skip CIO; run IDE chunks with --base-task only")
    p.add_argument(
        "--task-mode",
        choices=("override", "supplement"),
        default="override",
        help="Passed to run_ide_execution_agent",
    )
    p.add_argument("--iteration", action="store_true", help="IDE iteration_mode (stale SUBTASKS/DONE)")
    p.add_argument("--explore-only", action="store_true", help="IDE exploration_mode (artifacts optional)")
    p.add_argument("-q", "--quiet", action="store_true")
    args = p.parse_args()

    cio_model, cio_src = resolve_supervisor_cio_model((args.cio_model or "").strip() or None)
    coder_model = (args.coder_model or "").strip() or None
    wr_raw = (args.workspace_root or "").strip()
    workspace_root = Path(wr_raw) if wr_raw else None

    verbose = not args.quiet
    if verbose:
        print(
            f"[supervisor] llm.provider={settings.llm.provider!r} default_model={settings.llm.default_model!r} "
            f"cio_model={cio_model!r} (source={cio_src})",
            flush=True,
        )

    cfg = SupervisorConfig(
        scheme_session_dir=Path(args.scheme_session_dir),
        workspace_root=workspace_root,
        base_task=args.base_task,
        cio_model=cio_model,
        coder_model=coder_model,
        max_chunks=max(1, int(args.max_chunks)),
        chunk_rounds=max(1, int(args.chunk_rounds)),
        cio_context_chars=max(1000, int(args.cio_context_chars)),
        cio_timeout_sec=max(30, int(args.cio_timeout)),
        use_cio=not args.no_cio,
        task_mode=args.task_mode,
        iteration_mode=True if args.iteration else None,
        exploration_mode=True if args.explore_only else None,
        verbose=verbose,
    )

    result = run_supervisor_loop(cfg)
    print(json.dumps({"chunks": result.chunks, "exit_code": result.exit_code}, ensure_ascii=False, indent=2))
    raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
