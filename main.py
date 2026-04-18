"""
Entry point for the autonomous agent workflow.

Input: task (request + mode + project/session + opts). The process runs until the task
is done (idle or blocked). To continue research, start a new run with a new request.

Usage:
  python main.py "Your task or question"
  python main.py   # interactive: prompt for request
  python main.py --stdin   # read request from stdin
"""
import sys
import argparse
import json

from core.task_runners import run_research_task


def main():
    parser = argparse.ArgumentParser(
        description="Run a research task until completion. Provide a request; agents will plan, execute, and deliver.",
        epilog="Example: python main.py \"Explore whether factor X predicts returns.\"",
    )
    parser.add_argument(
        "request",
        nargs="*",
        help="Task or question (natural language). If omitted, run interactively or read from stdin.",
    )
    parser.add_argument("--stdin", action="store_true", help="Read request from stdin.")
    parser.add_argument("--no-interactive", action="store_true", help="If no request and not --stdin, exit with usage.")
    parser.add_argument(
        "--mode",
        choices=["design_only", "scheme_agent", "execution_prep", "ide_execution_agent"],
        default="design_only",
        help="Run mode: design_only; scheme_agent; execution_prep (copy scheme under <session>/project/execution_prep/); "
        "ide_execution_agent (execute from scheme artifacts only if no request; set --scheme-session-dir).",
    )
    parser.add_argument("--model", default="", help="Model name (scheme_agent, ide_execution_agent).")
    parser.add_argument("--lang", default="", choices=("", "en", "zh"), help="Output language (used by scheme_agent).")
    parser.add_argument("-q", "--quiet", action="store_true", help="Less verbose (used by scheme_agent).")
    parser.add_argument("--project", default="default", help="Project name under runs workspace.")
    parser.add_argument("--session", default="", help="Optional session id (auto-generated if empty).")
    parser.add_argument(
        "--scheme-session-dir",
        default="",
        help="Scheme session dir with artifacts/ (execution_prep, ide_execution_agent).",
    )
    parser.add_argument("--workspace-root", default=".", help="Workspace root for execution_prep output.")
    parser.add_argument(
        "--output-subdir",
        default="",
        help="execution_prep: optional legacy path under workspace root; empty = use <session>/project/execution_prep/.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=120,
        help="Max LLM+tool rounds for ide_execution_agent mode.",
    )
    args = parser.parse_args()

    request = _get_request(args)
    ide_exec_scheme_only = args.mode == "ide_execution_agent" and (args.scheme_session_dir or "").strip()
    if not request or not request.strip():
        if ide_exec_scheme_only:
            request = ""
        else:
            parser.print_help()
            print("\nNo request provided.")
            if not args.no_interactive:
                try:
                    request = input("\nRequest (or Ctrl-D to exit): ").strip()
                except EOFError:
                    pass
            if not request or not request.strip():
                sys.exit(0)

    task = {
        "request": request,
        "mode": args.mode,
        "model": args.model,
        "lang": args.lang,
        "verbose": (not args.quiet),
        "project": args.project,
        "session": args.session,
        "scheme_session_dir": args.scheme_session_dir,
        "workspace_root": args.workspace_root,
        "output_subdir": (args.output_subdir or "").strip() or None,
        "max_rounds": int(args.max_rounds),
    }
    result = run_research_task(task)
    print(_canonical_json(result))


def _get_request(args) -> str:
    if args.stdin:
        return sys.stdin.read().strip()
    return " ".join(args.request).strip() if args.request else ""


def _canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
