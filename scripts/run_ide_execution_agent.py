#!/usr/bin/env python3
"""
Autonomous IDE execution agent: LLM uses workspace_read / workspace_grep / workspace_write / workspace_list /
terminal_run (via LocalIDEAdapter) to implement code and run experiments after scheme phase.

Normally requires a completed scheme session directory with all four ``artifacts/*.md`` files; use ``--explore-only`` (or ``INVERST_IDE_EXPLORATION=1``) when those files may be absent (EDA / probe pass only).

Consolidated rule index (scheme, Override, modeling order): ``docs/reference/ide_execution_rules.md``.

**Default (no --task):** execution follows **only** the scheme package (research_plan, derivation, architecture_draft, experiment_design).

Example:
  python scripts/run_ide_execution_agent.py out/algo_alpha/v3

Optional extra instructions (wrap --task text in straight quotes; curly/smart quotes from editors break parsing):
  python scripts/run_ide_execution_agent.py out/algo_alpha/v3 \\
    --task "Narrow to CPCV skeleton only this run"

  # With --task, the agent must write project/outputs/scheme_alignment_audit.md (step 0) before claiming alignment fixes:
  python scripts/run_ide_execution_agent.py out/algo_alpha/v3 \\
    --task "Audit all modules vs artifacts; fix gaps; then continue experiments."

  # --task with no string is allowed (same as omitting --task):
  python scripts/run_ide_execution_agent.py out/algo_alpha/v3 --max-rounds 200 --task

  # Supplementary instructions (NOT a full Override — no mandatory scheme_alignment_audit.md first):
  python scripts/run_ide_execution_agent.py out/algo_alpha/v3 \\
    --supplement --task "Optimize compute: vectorize hot paths in src/; profile with a smoke run."

Writes are confined to ``<session>/project/``: code under ``project/src/``, run artifacts under ``project/outputs/`` (override with ``INVERST_IDE_OUTPUTS_SUBDIR``). No time-stamped folders.

The first user message is scheme- and SUBTASKS-driven; ``REPORT_TEMPLATE.md`` is on disk only (not embedded) to save context.

Env — model (CLI --model wins):
  INVERST_CODER_MODEL, INVERST_IDE_EXEC_AGENT_MODEL — see config/agents.yaml ide_execution.coder_model.

Env — ``--task`` translation (non-English → English before the coder sees Override; default on):
  INVERST_IDE_TRANSLATE_TASK — ``0`` / ``false`` / ``off`` to disable; ``1`` / ``true`` to force on.
  Optional ``ide_execution.task_translate_model`` in agents.yaml uses a separate model for that one translation call.

Global LLM routing comes from config/settings.yaml (``llm.provider``, ``ollama.api_base``). That file is loaded from the **repository root** even if your shell cwd is elsewhere — if you previously saw OpenAI / gpt-4o-mini, cwd-based load was missing the file and fell back to API defaults.

Env — exploration / EDA (CLI ``--explore-only`` wins over env):
  INVERST_IDE_EXPLORATION — ``1`` / ``true`` / ``on`` when scheme artifacts may be missing (same behavior as ``--explore-only``).

Env — limits (see docs/guides/ide_context_budget.md; defaults in config/agents.yaml ide_execution):
  INVERST_IDE_SKILLS — compact | full; unset uses yaml skills_inject.
  INVERST_IDE_RULES_MAX_CHARS — cap for injected docs/reference/ide_execution_rules.md (system prompt).
  INVERST_IDE_SCHEME_MAX_CHARS, INVERST_IDE_DATA_FIRST_MAX, INVERST_IDE_SESSION_MAX — snippet sizes.
  INVERST_IDE_LLM_TIMEOUT — chat_completion timeout (seconds).
  INVERST_IDE_OUTPUTS_SUBDIR — subdirectory under project/ for run outputs (default: outputs).
  INVERST_IDE_TOOL_RESULT_MAX_CHARS — max tool JSON per message.
  INVERST_IDE_ARTIFACT_READ_MAX_CHARS — higher cap for …/artifacts/ reads.
  INVERST_IDE_COERCE_TOOL_CALLS — 1 (default): parse tool JSON from assistant text when API omits tool_calls (Ollama).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.execution_agent import run_ide_execution_agent
from core.scheme_paths import resolve_workspace_root_cli_arg


def main() -> None:
    p = argparse.ArgumentParser(description="IDE execution agent (LLM + repo tools)")
    p.add_argument(
        "scheme_session_dir",
        nargs="?",
        help="Path to session dir containing artifacts/ (e.g. out/algo_alpha/v3)",
    )
    p.add_argument(
        "--task",
        nargs="?",
        default="",
        const="",
        metavar="TEXT",
        help="Optional instructions. Default: treated as **Override** (scheme_alignment_audit + appendix). Use with --supplement for focused asks without that gate.",
    )
    p.add_argument(
        "--supplement",
        action="store_true",
        help="Treat --task as supplementary only (no Override appendix; agent must edit src/ or write outputs/supplement_blocked.md). Requires --task TEXT.",
    )
    p.add_argument(
        "--iteration",
        action="store_true",
        help="Follow-up run: inject iteration prompts — stale SUBTASKS [x] / project/DONE do not authorize DONE; require "
        "src/ change or outputs/iteration_blocked.md + review_gate update. Env: INVERST_IDE_ITERATION=1.",
    )
    p.add_argument(
        "--explore-only",
        action="store_true",
        help="Exploration / EDA mode: the four scheme artifacts under artifacts/ may be missing; no locked acceptance "
        "claims. Env: INVERST_IDE_EXPLORATION=1.",
    )
    p.add_argument(
        "--workspace-root",
        default="",
        metavar="PATH",
        help="Workspace root for IDE tools. Default: from config (paths.workspace_root or parent of runs_dir).",
    )
    p.add_argument("--model", default="", help="LLM model id")
    p.add_argument("--max-rounds", type=int, default=120, help="LLM+tool rounds per process (default 120)")
    p.add_argument("-q", "--quiet", action="store_true")
    args = p.parse_args()

    sid = (args.scheme_session_dir or "").strip()
    if not sid:
        p.print_help()
        raise SystemExit(2)
    if args.supplement and not (args.task or "").strip():
        p.error("--supplement requires non-empty --task TEXT")

    result = run_ide_execution_agent(
        task=args.task,
        task_mode="supplement" if args.supplement else "override",
        scheme_session_dir=Path(sid),
        workspace_root=resolve_workspace_root_cli_arg(args.workspace_root),
        model=(args.model or "").strip() or None,
        max_rounds=int(args.max_rounds),
        verbose=not args.quiet,
        iteration_mode=(True if args.iteration else None),
        exploration_mode=(True if args.explore_only else None),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result.get("status") not in ("success",):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
