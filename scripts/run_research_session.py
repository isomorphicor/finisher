#!/usr/bin/env python3
"""
Skill-first default entry: scheme phase → optional execution prep → IDE execution agent.

This script is **independent** of ``run_autonomy_loop.py`` (deprecated). It uses the same
linear pipeline as ``run_scheme_then_ide.py`` via ``core.research_session_pipeline`` — one process,
no outer orchestration loop. Long-term work should compose **skills** (policy + ops playbooks in
``docs/skills/``) and runtime tools; see ``docs/skills/ARCHITECTURE.md``.

**Basic (scheme → prep → IDE):**

  python scripts/run_research_session.py --project algo_alpha --ide-max-rounds 200 \\
    "Your research task for the scheme phase"

**EDA → scheme → full experiment (recommended when data is unfamiliar):** Phase 0 exploration IDE
(``--eda-first``), then scheme, then prep, then final IDE. The **positional scheme task** (data paths,
constraints) is **always included** in Phase 0 so the agent probes real files — not only under
``project/``. If Phase 0 succeeds, Phase 1 (scheme) gets a host prefix instructing ``read_file`` on
``project/outputs/eda_report.md`` before writing artifacts. Use ``--explore-task`` for extra EDA-only lines;
use ``--ide-task`` for implementation + reporting.

  python scripts/run_research_session.py --project algo_alpha --session main --scheme-max-rounds 30 \\
    --eda-first \\
    --explore-task "EDA：数据字典、时间范围、标签与收益相关字段；输出 project/outputs/eda_report.md；不做 acceptance。" \\
    --ide-task "按 artifacts 与 SUBTASKS 实现实验；完成 review_gate；给出可复现命令。" \\
    --full-experiment-report \\
    --ide-max-rounds 200 \\
    "你的研究问题与约束（scheme 阶段）"

``--full-experiment-report`` appends a hint for **return/risk vs baseline**, costs, and limitations
in the final IDE phase (still subject to ``quant_soul`` / scheme acceptance rules).

Workspace root defaults from config/settings.yaml (``paths.workspace_root`` or parent of ``paths.runs_dir``);
pass ``--workspace-root PATH`` to override.

Flags match ``run_scheme_then_ide.py`` (same underlying pipeline).
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
        description="Research session: scheme → prep → IDE (skill-first recommended entry).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_scheme_prep_ide_arguments(p)
    args = p.parse_args()
    try:
        out, code = run_scheme_prep_ide_pipeline(args, log_prefix="[run_research_session]")
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
