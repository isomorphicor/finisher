#!/usr/bin/env python3
"""
Run scheme phase → optional execution prep → IDE execution agent in one process.

Example (repo root):
  python scripts/run_scheme_then_ide.py --project algo_alpha "Build a CPCV baseline for panel alpha"

  python scripts/run_scheme_then_ide.py --project algo_alpha --scheme-max-rounds 40 --ide-max-rounds 200 \\
    --ide-task "Implement baseline first; defer heavy optimize" "Your scheme task"

The scheme phase **creates** ``<project>/<session>/`` early; the four ``artifacts/*.md`` files appear when the agent **finishes** writing them. If ``--scheme-max-rounds`` is too low or the run stops early, **Phase 2/3 are skipped** and the JSON will list ``scheme_artifacts_missing`` instead of calling the IDE with ``E_SCHEME``.

Implementation is shared with ``scripts/run_research_session.py`` via ``core.research_session_pipeline``.

See also: docs/guides/command_examples.md, docs/skills/ARCHITECTURE.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.research_session_pipeline import add_scheme_prep_ide_arguments, run_scheme_prep_ide_pipeline


def main() -> None:
    p = argparse.ArgumentParser(
        description="Scheme agent → optional execution prep → IDE execution agent (single invocation).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_scheme_prep_ide_arguments(p)
    args = p.parse_args()
    try:
        out, code = run_scheme_prep_ide_pipeline(args, log_prefix="[scheme_then_ide]")
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
