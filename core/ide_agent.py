"""
IDE execution agent (v2): one module — LLM + LocalIDEAdapter tools + scheme session.

Deliberately **no** chat-history compression/folding (that layer caused more harm than help).
Tool results are capped via ``agents.yaml`` / env; Ollama may put tool JSON in ``content`` — we coerce.

Public API: ``run_ide_execution_agent`` (same signature as before). Facade: ``core/execution_agent``.
Default rules: ``docs/reference/ide_core_rules.md`` (+ short intro/loop). Optional **extended** profile appends
``docs/reference/ide_execution_rules.md`` (see ``get_ide_execution_ide_rules_profile`` in ``ide_execution_config``).
"""
from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import settings
from core.llm import LLMCompletionError, LLMService
from core.ide_execution_config import (
    get_ide_execution_command_allowlist,
    get_ide_execution_ide_rules_profile,
    get_ide_execution_int,
    get_ide_execution_skills_mode,
    get_ide_execution_translate_task_enabled,
    get_ide_execution_write_scope,
    resolve_ide_execution_model,
    resolve_ide_execution_task_translate_model,
)
from core.translate import translate_to_english_if_needed
from runtime.adapters.local_adapter import LocalIDEAdapter
from skills.ide_execution import build_allowed_write_prefixes, get_ide_execution_tools

REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_FIRST_SKILL_PATH = REPO_ROOT / "docs/skills/ops/data-first-execution/SKILL.md"
_SESSION_PROJECT_CODE_SKILL_PATH = REPO_ROOT / "docs/skills/ops/session-project-code/SKILL.md"
IDE_CORE_RULES_PATH = REPO_ROOT / "docs/reference/ide_core_rules.md"
IDE_RULES_PATH = REPO_ROOT / "docs/reference/ide_execution_rules.md"
EXECUTION_REPORT_TEMPLATE_PATH = REPO_ROOT / "docs/templates/execution_report_ide.md"


def _repo_tool_prefix(workspace_root: Path) -> str:
    """Prefix for `docs/`, `skills/` when ``workspace_root`` is a parent of ``REPO_ROOT`` (e.g. …/Project vs …/Project/finish)."""
    wr = workspace_root.resolve()
    rr = REPO_ROOT.resolve()
    try:
        rel = rr.relative_to(wr)
    except ValueError:
        return ""
    s = str(rel).replace("\\", "/").strip()
    if not s or s == ".":
        return ""
    return s.rstrip("/") + "/"


def _append_repo_tool_paths_system_note(base: str, repo_tool_prefix: str) -> str:
    if not repo_tool_prefix:
        return base
    return (
        base
        + "\n\n---\n## Tool paths (multi-root workspace)\n"
        + "The filesystem **workspace root** may be **above** the Inverst git checkout. "
        + "Instructions that mention `docs/`, `skills/`, or `config/` at **repository** root are under this prefix:\n\n"
        + f"- **Prefix:** `{repo_tool_prefix}`\n"
        + f"- Example `workspace_read`: `{repo_tool_prefix}docs/reference/ide_core_rules.md`\n"
        + f"- Example `workspace_grep` `path`: `{repo_tool_prefix}docs/reference`\n\n"
        + "Do **not** assume `docs/` exists at the workspace root unless you listed that directory. "
        + "Scheme `artifacts/` and `project/` paths in the user message are already correct for this workspace.\n"
    )

# Fallback if ide_execution_rules.md is missing or OVERRIDE markers are broken.
_OVERRIDE_FOLLOW_THROUGH_FALLBACK = (
    "**Override follow-through (mandatory):** write `project/outputs/scheme_alignment_audit.md` first; then diff "
    "`artifacts/` vs `project/src/`, fix gaps, re-run. See `docs/reference/ide_execution_rules.md`."
)
_override_followthrough_cache: str | None = None

REQUIRED_SCHEME_ARTIFACTS = (
    "research_plan.md",
    "derivation.md",
    "architecture_draft.md",
    "experiment_design.md",
)

# Only these tools reset the stall counter. ``workspace_read`` / ``workspace_list`` / ``workspace_grep`` do not —
# otherwise the model can loop on read/search + prose without producing code/output changes.
IDE_STALL_RESET_TOOLS = frozenset({"workspace_write", "terminal_run"})


def _first_line_is_done(body: str) -> bool:
    text = body.strip()
    if not text:
        return False
    return text.splitlines()[0].strip().casefold() == "done"


# Fallback if ide_core_rules.md is missing (keep tiny; prefer restoring the file).
IDE_CORE_RULES_FALLBACK = """# IDE core rules (fallback)

Accountability — No human code-review obligation; user cares about outputs/review_gate; you own correctness.
A — Information set + split protocol; portfolio defs; label ≠ tradable return unless proven; scheme alignment.
B — Scale-matched pipelines; estimate/smoke; job counts; Ollama queue per tag.
C — CatBoost first at scale; small data linear (OLS ok); joint multi-*y* before heavy paths; baseline bar; features→baseline→tune.
D — Exploration splits; one acceptance CPCV; pivot on overfit signals.
Autonomous — inspect src for cheaper/better approach vs B–D; document trade-offs in review_gate/WORKLOG; do not rely on user reminders.
Workflow — SUBTASKS (bookkeeping); review_gate completion+evidence before DONE (not SUBTASKS-only); Override audit; soul/stack on demand.
"""


def _load_ide_core_rules_for_system_prompt(*, max_chars: int) -> str:
    if not IDE_CORE_RULES_PATH.is_file():
        body = IDE_CORE_RULES_FALLBACK
    else:
        try:
            raw = IDE_CORE_RULES_PATH.read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = IDE_CORE_RULES_FALLBACK
        else:
            body = raw.strip()
            if body.startswith("---"):
                sp = body.split("---", 2)
                if len(sp) >= 3:
                    body = sp[2].strip()
    if len(body) > max_chars:
        body = (
            body[:max_chars].rstrip()
            + "\n\n[TRUNCATED — raise ide_execution.ide_core_rules_max_chars or INVERST_IDE_CORE_RULES_MAX_CHARS]\n"
        )
    return body


def _build_execution_agent_core() -> str:
    core_max = get_ide_execution_int("ide_core_rules_max_chars", "INVERST_IDE_CORE_RULES_MAX_CHARS", 12000)
    core_body = _load_ide_core_rules_for_system_prompt(max_chars=core_max)
    return (
        "You are the **IDE execution agent**. **No one is obligated to review your code** — the user cares about **outcomes**: "
        "reproducible **`project/outputs/`**, honest **`review_gate.md`**, and claims that survive scrutiny. **You are accountable** "
        "for methodology and correctness; self-critique and evidence are how you discharge that duty, not a handoff expecting a human "
        "audit. Change the repo **only** via tools "
        "(`workspace_*`, `terminal_run`, `workspace_grep`).\n\n"
        + core_body
        + "\n\n**Loop:** (1) `workspace_read` `artifacts/`. (2) `SUBTASKS.md`. (3) New `Next: #m` → `workspace_grep` `docs/` → "
        "`workspace_read`. (4) One module; `project/src/`, `project/outputs/`. (5) Before `[x]` on train/eval: multi-*y* → "
        "**cheap CatBoost baseline first** (group/weights + one fit); not CPCV+per-label before that. "
        "(5a) **Self-improvement (your duty, every run):** inspect `project/src/` for expensive or rule-violating patterns; "
        "apply or justify a **better** approach vs §B–D in **`review_gate`** / **`WORKLOG.md`** — do **not** wait for the user to name the issue. "
        "(5b) Before `DONE` or claiming **Sharpe / CPCV / portfolio** evidence: write **`project/outputs/review_gate.md`** from "
        "**`docs/templates/ide_review_gate.md`** — **Session completion** + evidence verdicts **pass**/**must_fix** (scheme-style review; "
        "**not** all-`[x]` SUBTASKS alone). Tier **R** unresolved → no `DONE` unless `[!]` waiver. "
        "(6) **`DONE` alone on the first line** ends the tool loop after **`review_gate`** allows completion and SUBTASKS is `[x]`/`[!]`.\n\n"
        "Extended tiers / Override appendix / combinatorics: `workspace_read` `docs/reference/ide_execution_rules.md` "
        "when you need detail.\n\n"
        "If tool calls appear only as JSON text (some local servers), the host may still execute them.\n"
    )


def _load_ide_extended_rules_block() -> str:
    if get_ide_execution_ide_rules_profile() != "extended":
        return ""
    rules_max = get_ide_execution_int("ide_rules_max_chars", "INVERST_IDE_RULES_MAX_CHARS", 32000)
    return (
        "\n---\n## Extended rules (ide_execution_rules.md)\n\n"
        + _load_ide_rules_for_system_prompt(max_chars=rules_max)
    )


def _strip_override_appendix_for_system_prompt(raw: str) -> str:
    """Remove OVERRIDE appendix (HTML comments) from rules file — that block is only for the user message."""
    start = "<!-- BEGIN:OVERRIDE_FOLLOW_THROUGH -->"
    end = "<!-- END:OVERRIDE_FOLLOW_THROUGH -->"
    if start in raw and end in raw:
        before, rest = raw.split(start, 1)
        _, after = rest.split(end, 1)
        return (before + after).strip()
    return raw.strip()


def _load_ide_rules_for_system_prompt(*, max_chars: int) -> str:
    if not IDE_RULES_PATH.is_file():
        return "[Missing docs/reference/ide_execution_rules.md in repo — restore from version control.]\n"
    try:
        raw = IDE_RULES_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "[Unreadable docs/reference/ide_execution_rules.md]\n"
    body = _strip_override_appendix_for_system_prompt(raw)
    if len(body) > max_chars:
        body = (
            body[:max_chars].rstrip()
            + "\n\n[TRUNCATED — raise ide_execution.ide_rules_max_chars or INVERST_IDE_RULES_MAX_CHARS]\n"
        )
    return body


def _get_override_followthrough() -> str:
    """Verbatim paragraph appended after ## Override (sourced from ide_execution_rules.md markers)."""
    global _override_followthrough_cache
    if _override_followthrough_cache is not None:
        return _override_followthrough_cache
    if not IDE_RULES_PATH.is_file():
        _override_followthrough_cache = _OVERRIDE_FOLLOW_THROUGH_FALLBACK
        return _override_followthrough_cache
    try:
        raw = IDE_RULES_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        _override_followthrough_cache = _OVERRIDE_FOLLOW_THROUGH_FALLBACK
        return _override_followthrough_cache
    start = "<!-- BEGIN:OVERRIDE_FOLLOW_THROUGH -->"
    end = "<!-- END:OVERRIDE_FOLLOW_THROUGH -->"
    if start not in raw or end not in raw:
        _override_followthrough_cache = _OVERRIDE_FOLLOW_THROUGH_FALLBACK
        return _override_followthrough_cache
    inner = raw.split(start, 1)[1].split(end, 1)[0].strip()
    _override_followthrough_cache = inner if inner else _OVERRIDE_FOLLOW_THROUGH_FALLBACK
    return _override_followthrough_cache


IDE_DATA_FIRST_COMPACT = (
    "Floor: `ide_core_rules.md` — CatBoost + cheap multi-*y* joint fit before CPCV/per-label; self-critique src/ vs §B–D "
    "before strong review_gate; user owes no code review — ship defensible outputs. NN vs ref MLP: `quant_tech_stack` + extended if needed."
)
IDE_SESSION_COMPACT = (
    "`ide_core_rules.md` default; optional `ide_execution.ide_rules_profile: extended` adds `ide_execution_rules.md`. "
    "`workspace_grep` → read. `Path(__file__)` → `project/`; session skill for MPS/CatBoost."
)

SCHEME_DRIVEN_EXECUTION_DIRECTIVE = (
    "Follow the **scheme**. **`SUBTASKS.md`**: **Progress** + per-line `[ ]`/`[x]`/`[!]`; one module at a time; **review** code before `[x]`. "
    "**Re-align** with **targeted** `artifacts/` sections for **Next: #m** (if current line is `[x]`, read docs for the **next** open module). "
    "**Each new module:** `workspace_grep` on `docs/` → then `workspace_read` (see rules **Workflow** step 3). "
    "Data: probe → **compact** glue. **Quality:** ask whether a **cheaper or more correct** implementation exists "
    "(methodology order, job counts); record trade-offs in **`review_gate`** / **`WORKLOG`** — not only when the user asks. "
    "**Results:** the user judges **outputs and claims**, not your source; make outputs self-sufficient (`ide_core_rules` *Accountability*)."
)

# Appended to system prompt when iteration_mode (CLI --iteration / INVERST_IDE_ITERATION) is on.
ITERATION_MODE_SYSTEM_NOTE = (
    "\n\n---\n**Iteration run (host):** Stale `project/DONE` or all-`[x]` SUBTASKS **do not** authorize completion here. "
    "You must still produce a **verifiable delta** (see user **Iteration run**). This **adds** to the default duty to "
    "**self-critique** (`ide_core_rules.md` *Autonomous improvement*) — it does not replace it.\n"
)


def _resolve_iteration_mode(explicit: bool | None) -> bool:
    """True when the host marks this run as a follow-up iteration (CLI or env)."""
    if explicit is True:
        return True
    if explicit is False:
        return False
    raw = (os.environ.get("INVERST_IDE_ITERATION") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _resolve_exploration_mode(explicit: bool | None) -> bool:
    """True for EDA/explore-only runs (`--explore-only` / INVERST_IDE_EXPLORATION) — scheme artifacts optional."""
    if explicit is True:
        return True
    if explicit is False:
        return False
    raw = (os.environ.get("INVERST_IDE_EXPLORATION") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


# Appended when exploration_mode (CLI --explore-only / INVERST_IDE_EXPLORATION).
EXPLORATION_MODE_SYSTEM_NOTE = (
    "\n\n---\n**Exploration mode:** The four scheme `artifacts/*.md` files may be missing. **Do not** claim CPCV acceptance, "
    "portfolio Sharpe, or production-ready evidence. Deliver **EDA / probes** under `project/outputs/` (e.g. `eda_report.md`). "
    "Raw datasets are often **outside** the session `project/` tree — follow **absolute paths or paths in the user task**, not only `project/data/`. "
    "Do **not** loop on endless similar `terminal_run` scripts — consolidate into `eda_report.md` via **`workspace_write`**.\n"
)

# Injected when exploration_mode and consecutive terminal_run rounds without workspace_write exceed warn threshold.
EXPLORATION_TERMINAL_STREAK_NUDGE = (
    "**Host (exploration anti-loop):** You have used **`terminal_run`** many times without **`workspace_write`**. "
    "Stop repeating similar pandas probes. **Immediately** use **`workspace_write`** to create or append "
    "`project/outputs/eda_report.md` with: schema summary, date span, label/return column definitions, and a short lookahead checklist. "
    "Then reply with **`DONE` on the first line** if the EDA scope is met, or **one** more targeted `terminal_run` only if a single critical gap remains."
)


def _scheme_snippets_for_ide(artifacts_dir: Path, scheme_max: int, *, exploration_mode: bool) -> list[str]:
    """Load scheme artifact text for the user prompt; placeholders in exploration mode when files are absent."""
    snippets: list[str] = []
    for name in REQUIRED_SCHEME_ARTIFACTS:
        p = artifacts_dir / name
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="replace")
            if len(text) > scheme_max:
                text = text[:scheme_max] + "\n\n[TRUNCATED]\n"
        elif exploration_mode:
            text = (
                f"*(Exploration phase — `{name}` is not present yet. Do not treat as locked experiment design.)*"
            )
        else:
            text = ""
        snippets.append(f"### {name}\n\n{text}")
    return snippets


def _build_exploration_user_message(
    *,
    project_rel: str,
    artifacts_rel: str,
    outputs_rel: str,
    workspace_root: Path,
    repo_tool_prefix: str = "",
    eda_report_rel: str,
    scheme_snippets: list[str],
    task_stripped: str,
    task_mode: str = "override",
) -> str:
    """User message when scheme artifacts may be incomplete (EDA / probe pass)."""
    supplement = bool(task_stripped) and task_mode.strip().lower() == "supplement"
    doc_grep_root = f"{repo_tool_prefix}docs/" if repo_tool_prefix else "docs/"
    doc_grep_path = f"{repo_tool_prefix}docs/reference" if repo_tool_prefix else "docs/reference"
    parts = [
        "## Mission (exploration mode)",
        "This run is **EDA / data exploration only**. The scheme package under `artifacts/` may be **incomplete**.",
        "",
        "1) **Probes first:** use **`terminal_run`** and **`workspace_write`** to record dtypes, row counts, date span, keys, and missingness — save to **`eda_report.md`** (or equivalent) under `project/outputs/`.",
        f"2) **Read policies as needed:** `{doc_grep_root}` (e.g. `workspace_grep` on `{doc_grep_path}` for time-safety / data QA).",
        "3) **Forbidden in this mode:** claiming **CPCV acceptance**, **path-multiplicity portfolio Sharpe**, **locked acceptance protocol**, or **production** readiness. If scheme files are placeholders below, they are **not** approved designs.",
        "4) **Anti-stall:** alternate **`workspace_write`** / **`terminal_run`** with reads — do not spend all rounds on `workspace_read` alone. "
        "**Anti-loop:** do not repeat similar `terminal_run` one-liners indefinitely — batch findings into **`eda_report.md`** (the host may nudge or stop the run if probes repeat without writes).",
        "5) **Finish:** When probes match the task, reply **`DONE` as the only text on the first line** (optional summary after a blank line). "
        f"`review_gate.md` is optional; if used, state scope **exploration only**.",
        "",
        "## Paths",
        f"- Workspace: `{workspace_root}`",
        (
            f"- **Inverst repo (policies, `docs/`, `skills/`):** prefix `{repo_tool_prefix}` on tool paths."
            if repo_tool_prefix
            else "- **Inverst repo:** workspace root may be the git checkout — use `docs/…` as in the system prompt."
        ),
        f"- Scheme dir (may be incomplete): `{artifacts_rel}/`",
        f"- Writes: `{project_rel}/` (code: `{project_rel}/src/`, outputs: `{outputs_rel}/`)",
        f"- Target EDA file: `{eda_report_rel}`",
        "- **Input data:** Features/labels often live **outside** this session (e.g. `config/settings.yaml` `paths.data_dir` or "
        "**absolute paths** in the task). Probe those paths with `terminal_run` — do **not** skip EDA because nothing appears under `project/` except outputs.",
        "",
        "## Directive",
        "See system prompt **Exploration mode** and `docs/skills/ops/data-first-execution/SKILL.md` (probe → compact loaders).",
        "",
        "## Scheme snippets (may include placeholders)",
        *scheme_snippets,
    ]
    if task_stripped and supplement:
        parts.extend(["", "## Supplementary instructions", task_stripped])
    elif task_stripped:
        parts.extend(["", "## Task", task_stripped])
    return "\n".join(parts)


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw, 10))
    except ValueError:
        return default


def _ide_outputs_subdir() -> str:
    """Stable subdirectory under ``project/`` for run artifacts (default ``outputs``)."""
    raw = (os.environ.get("INVERST_IDE_OUTPUTS_SUBDIR") or "outputs").strip()
    sub = raw.strip("/").replace("\\", "/") if raw else "outputs"
    return sub or "outputs"


def _build_user_message(
    *,
    project_rel: str,
    artifacts_rel: str,
    outputs_rel: str,
    workspace_root: Path,
    repo_tool_prefix: str = "",
    eda_report_rel: str,
    scheme_snippets: list[str],
    task_stripped: str,
    task_mode: str = "override",
    iteration_mode: bool = False,
) -> str:
    """
    task_mode:
      - ``override`` (default): ``--task`` is a full Override — mandatory audit path + appendix.
      - ``supplement``: ``--task`` is extra instructions only (e.g. optimize efficiency) — no forced
        ``scheme_alignment_audit.md``; agent must still change code or write why not.
    """
    supplement = bool(task_stripped) and task_mode.strip().lower() == "supplement"
    doc_grep_root = f"{repo_tool_prefix}docs/" if repo_tool_prefix else "docs/"
    doc_grep_path = f"{repo_tool_prefix}docs/reference" if repo_tool_prefix else "docs/reference"
    parts = [
        "## Mission",
        "1) Ground in `artifacts/*.md` (paths below): **first** pass can be broad enough to draft SUBTASKS; **later**, re-read **only** passages tied to **Next: #m** (not the full tree each time) — see system prompt *Periodic scheme alignment*.",
        f"2) Write or refresh `{project_rel}/SUBTASKS.md` — **must** include **Progress: k/N · Next: #m · Last updated:** at the top and "
        "`[ ]` / `[x]` / `[!]` on each **numbered** module line (see system prompt). Merge with existing file if present; do not drop completed `[x]`.",
        f"2b) **Before coding each new `Next: #m`** — **`workspace_grep`** under `{doc_grep_root}` then **`workspace_read`** (e.g. pattern `Backtest|Sharpe|C\\(N`, path `{doc_grep_path}`) — see system prompt **Workflow** step 3.",
        "3) **One module at a time** — follow **Next: #m**; code in `project/src/`, outputs in `project/outputs/` (or paths below). When the step **works**, **review** the code (elegant, minimal), then set `[x]` and update **Progress**.",
        "   **Data-heavy steps:** run a **small probe** (`terminal_run`: columns/dtypes/nrows → save to `outputs/`) before writing a large loader; loaders stay **short** and **explicit** after the probe — see system prompt *Data loading & EDA*.",
        "   **Long-run alignment:** check **`SUBTASKS.md`** (**Next: #m**); **`workspace_read`** the **corresponding** scheme sections (and EDA if needed). If that line is already **`[x]`**, align to the **next** open module. Do **not** re-read every artifact file each time; see *Periodic scheme alignment*.",
    ]
    if task_stripped and not supplement:
        parts.append(
            "   **Override gate:** **`## Override`** is present — complete **Override follow-through** in order. "
            f"Step **(0)** is blocking: write `{outputs_rel}/scheme_alignment_audit.md` **before** claiming alignment/correction is done or before pushing new experiment work; see system prompt *User override*."
        )
    if task_stripped and supplement:
        parts.append(
            "   **Supplementary run:** Follow **## Supplementary instructions** below. You must **either** edit at least one file under "
            f"`{project_rel}/src/` with **`workspace_write`** (performance/behavior change) **or** write `{outputs_rel}/supplement_blocked.md` "
            "with a short reason code cannot change yet. **Do not** spend all rounds on reads alone; aim to touch code or the blocked note within the first several tool rounds."
        )
    if iteration_mode:
        parts.append(
            "   **Iteration run (host):** Treat **Progress / all `[x]`** and any **`DONE` file** as **non-authoritative** until you "
            "re-check policy vs `project/src/` (e.g. `workspace_grep` for per-label loops vs joint multi-target). This pass is **not** done "
            "because a previous run marked complete."
        )
    parts.extend(
        [
        "4) **Finish the run:** write **`review_gate.md`** with **Session completion (review)** = **pass** (substance vs `artifacts/`/`outputs/`/`src/` — "
        "**not** inferred from SUBTASKS checkboxes alone). Then, when every numbered item is `[x]` or waived `[!]`, reply **`DONE` as the only text on the first line** "
        "(optional summary after a blank line). The host stops only on that line; **`stall`** exit in the runner is a safety valve, not a substitute for **`review_gate`**.",
        "",
        "## Paths",
        f"- Workspace: `{workspace_root}`",
        (
            f"- **Inverst repo (policies, `docs/`, `skills/`):** prefix `{repo_tool_prefix}` on tool paths — e.g. `{repo_tool_prefix}docs/reference/…`"
            if repo_tool_prefix
            else "- **Inverst repo:** workspace root is the git checkout — use `docs/…` as in the system prompt."
        ),
        f"- Scheme: `{artifacts_rel}/`",
        f"- Writes: `{project_rel}/` (code: `{project_rel}/src/`, run outputs: `{outputs_rel}/`)",
        *(
            [
                f"- **Session implementation:** use `workspace_write` **only** under `{project_rel}/` — "
                f"not under `{repo_tool_prefix}` (that is the Inverst checkout for docs/policies/skills, read-only for your code).",
            ]
            if repo_tool_prefix
            else []
        ),
        f"- EDA file: `{eda_report_rel}`",
        "",
        "## Directive",
        (
            SCHEME_DRIVEN_EXECUTION_DIRECTIVE.replace("`docs/`", f"`{repo_tool_prefix}docs/`")
            if repo_tool_prefix
            else SCHEME_DRIVEN_EXECUTION_DIRECTIVE
        ),
        ],
    )
    if task_stripped and supplement:
        parts.extend(["", "## Supplementary instructions", task_stripped])
    elif task_stripped:
        parts.extend(["", "## Override", task_stripped, "", _get_override_followthrough()])
    if iteration_mode:
        parts.extend(
            [
                "",
                "## Iteration run (host-enforced)",
                "This process was started with **iteration mode** (`--iteration` / `INVERST_IDE_ITERATION=1`).",
                "",
                "1. **Stale completion:** `SUBTASKS.md` may show all `[x]` and `project/DONE` may exist — **ignore** as proof of closure. "
                "Compare implementation to `docs/reference/ide_core_rules.md` (e.g. joint multi-*y* before heavy CPCV / per-label loops) and to your task.",
                "",
                f"2. **Deliverable before first-line `DONE`:** At least one of: (a) **`workspace_write`** under `{project_rel}/src/` "
                f"(or `project/` as needed) fixing the gap; (b) **`workspace_write`** `{outputs_rel}/iteration_blocked.md` — short, with evidence "
                "(e.g. `terminal_run` / grep output) if you truly cannot change code; (c) update **`{outputs_rel}/review_gate.md`** for this iteration "
                "(must_fix vs pass), not checkbox-only bookkeeping.",
                "",
                "3. **Anti-stall:** Do not end with only reads — use **`terminal_run`** or **`workspace_write`** in the same work stretch before `DONE`.",
                "",
                "4. **Optional:** Add an **Iteration** subsection to `SUBTASKS.md` with `[ ]` items so Progress reflects real follow-up.",
            ]
        )
    parts.extend(["", "## Scheme snippets", *scheme_snippets])
    return "\n".join(parts)


def _load_ops_skill_body(path: Path, *, fallback: str, max_chars: int) -> str:
    if not path.is_file():
        return fallback
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return fallback
    if text.startswith("---"):
        sp = text.split("---", 2)
        if len(sp) >= 3:
            text = sp[2].strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[TRUNCATED]"
    return text


def _load_execution_report_template(*, max_chars: int = 2000) -> str:
    if not EXECUTION_REPORT_TEMPLATE_PATH.is_file():
        return "# execution_report.md\n\nFill metrics, commands, blockers.\n"
    try:
        text = EXECUTION_REPORT_TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "# execution_report.md\n\nFill metrics, commands, blockers.\n"
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[TRUNCATED]"
    return text


def _system_message(*, repo_tool_prefix: str = "", iteration_mode: bool = False, exploration_mode: bool = False) -> str:
    df_fb = "EDA before heavy modeling; then SUBTASKS-driven experiments."
    ss_fb = "Paths / MPS / GBDT notes — see session-project-code SKILL."
    base = _build_execution_agent_core() + _load_ide_extended_rules_block()
    if iteration_mode:
        base = base + ITERATION_MODE_SYSTEM_NOTE
    if exploration_mode:
        base = base + EXPLORATION_MODE_SYSTEM_NOTE
    mode = get_ide_execution_skills_mode()
    if mode in ("full", "1", "true", "yes", "all"):
        df_max = get_ide_execution_int("data_first_skill_max_chars", "INVERST_IDE_DATA_FIRST_MAX", 6000)
        ss_max = get_ide_execution_int("session_skill_max_chars", "INVERST_IDE_SESSION_MAX", 8000)
        return _append_repo_tool_paths_system_note(
            base
            + "\n---\n### Data-first (SKILL)\n"
            + _load_ops_skill_body(_DATA_FIRST_SKILL_PATH, fallback=df_fb, max_chars=df_max)
            + "\n---\n### Session project (SKILL)\n"
            + _load_ops_skill_body(_SESSION_PROJECT_CODE_SKILL_PATH, fallback=ss_fb, max_chars=ss_max),
            repo_tool_prefix,
        )
    return _append_repo_tool_paths_system_note(
        base + "\n---\n**Compact:**\n" + IDE_DATA_FIRST_COMPACT + "\n\n" + IDE_SESSION_COMPACT,
        repo_tool_prefix,
    )


def _is_artifacts_path(path_s: str) -> bool:
    return "/artifacts/" in (path_s or "").replace("\\", "/").lower()


def _truncate_tool_result(result: dict[str, Any], *, max_chars: int) -> dict[str, Any]:
    """Cap tool JSON size; larger budget for …/artifacts/ reads."""
    if max_chars <= 200:
        return {"status": str(result.get("status", "")), "report": {"_note": "truncated"}}
    r = copy.deepcopy(result)
    rep = r.get("report")
    path_s = str(rep.get("path") or "") if isinstance(rep, dict) else ""
    art_max = get_ide_execution_int("artifact_read_max_chars", "INVERST_IDE_ARTIFACT_READ_MAX_CHARS", 98304)
    eff = max(max_chars, art_max) if _is_artifacts_path(path_s) else max_chars

    if isinstance(rep, dict):
        c = rep.get("content")
        if isinstance(c, str):
            cap = min(len(c), eff - 2500) if _is_artifacts_path(path_s) else max(1200, min(8000, eff - 400))
            if len(c) > cap:
                rep["content"] = c[:cap] + f"\n\n...[TRUNCATED {len(c)} chars]"
        for key in ("stdout", "stderr"):
            v = rep.get(key)
            if isinstance(v, str):
                cap2 = max(800, min(6000, eff // 2))
                if len(v) > cap2:
                    rep[key] = v[:cap2] + "\n...[TRUNCATED]"
    out = json.dumps(r, ensure_ascii=False)
    if len(out) > eff and isinstance(rep, dict) and isinstance(rep.get("content"), str) and _is_artifacts_path(path_s):
        for _ in range(12):
            if len(json.dumps(r, ensure_ascii=False)) <= eff:
                break
            rep["content"] = rep["content"][: max(4000, len(rep["content"]) * 2 // 3)] + "\n...[fit budget]"
    out = json.dumps(r, ensure_ascii=False)
    if len(out) > eff:
        return {"status": r.get("status"), "report": {"_truncated": True, "_chars": len(out)}, "errors": r.get("errors")}
    return r


# --- Ollama: tool JSON in content ---


def _coerce_parse_tool_calls(content: str) -> list[dict[str, Any]]:
    if not content or not isinstance(content, str):
        return []

    def strip_fence(s: str) -> str:
        s = s.strip()
        if not s.startswith("```"):
            return s
        lines = s.split("\n")
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def args_to_str(args: Any) -> str:
        if args is None:
            return "{}"
        if isinstance(args, str):
            return args
        if isinstance(args, (dict, list)):
            return json.dumps(args, ensure_ascii=False)
        return json.dumps({"value": args}, ensure_ascii=False)

    def norm_one(obj: dict[str, Any], idx: int) -> dict[str, Any] | None:
        fn = obj.get("function")
        if isinstance(fn, dict) and fn.get("name"):
            return {
                "id": str(obj.get("id") or f"call_{idx}"),
                "type": "function",
                "function": {"name": str(fn["name"]), "arguments": args_to_str(fn.get("arguments"))},
            }
        if obj.get("name") and "arguments" in obj:
            return {
                "id": str(obj.get("id") or f"call_{idx}"),
                "type": "function",
                "function": {"name": str(obj["name"]), "arguments": args_to_str(obj.get("arguments"))},
            }
        return None

    s = strip_fence(content)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        dec = json.JSONDecoder()
        data = None
        for i, ch in enumerate(s):
            if ch in "{[":
                try:
                    data = dec.raw_decode(s, i)[0]
                    break
                except json.JSONDecodeError:
                    continue
    if data is None:
        return []
    if isinstance(data, dict):
        one = norm_one(data, 0)
        return [one] if one else []
    if isinstance(data, list):
        out: list[dict[str, Any]] = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                one = norm_one(item, i)
                if one:
                    out.append(one)
        return out
    return []


def _function_to_dict(fn: Any) -> dict[str, Any]:
    """OpenAI tool ``function`` may be dict or SDK object with .name / .arguments."""
    if fn is None:
        return {}
    if isinstance(fn, dict):
        name = fn.get("name")
        if name is None or (isinstance(name, str) and not name.strip()):
            return {}
        args = fn.get("arguments", "{}")
        if isinstance(args, dict) or isinstance(args, list):
            args = json.dumps(args, ensure_ascii=False)
        elif not isinstance(args, str):
            args = json.dumps(args, ensure_ascii=False) if args is not None else "{}"
        return {"name": str(name).strip(), "arguments": args}
    name = getattr(fn, "name", None)
    if name is None or (isinstance(name, str) and not str(name).strip()):
        return {}
    args = getattr(fn, "arguments", None)
    if isinstance(args, str):
        arg_s = args
    elif args is None:
        arg_s = "{}"
    else:
        arg_s = json.dumps(args, ensure_ascii=False)
    return {"name": str(name).strip(), "arguments": arg_s}


def _tc_fn(tc: Any) -> dict[str, Any]:
    if isinstance(tc, dict):
        return _function_to_dict(tc.get("function"))
    return _function_to_dict(getattr(tc, "function", None))


def _tc_id(tc: Any) -> str:
    if isinstance(tc, dict):
        return str(tc.get("id") or "")
    return str(getattr(tc, "id", None) or "")


def _tool_call_to_openai_dict(tc: Any, idx: int) -> dict[str, Any]:
    """Force each tool call into OpenAI dict shape so name/arguments are never lost (LiteLLM SDK objects)."""
    fn = _tc_fn(tc)
    if not fn.get("name") and hasattr(tc, "model_dump"):
        md = tc.model_dump()
        fn = _function_to_dict(md.get("function"))
    tid = _tc_id(tc) or f"call_{idx}"
    return {
        "id": tid,
        "type": "function",
        "function": {
            "name": fn.get("name") or "",
            "arguments": fn.get("arguments", "{}") if isinstance(fn.get("arguments"), str) else json.dumps(
                fn.get("arguments") or {}, ensure_ascii=False
            ),
        },
    }


def _tool_loop(
    *,
    llm: LLMService,
    model: str,
    messages: list[dict[str, Any]],
    tools_spec: list[dict[str, Any]],
    tools_impl: dict[str, Any],
    max_rounds: int,
    llm_timeout: int,
    verbose: bool,
    outputs_rel: str,
    exploration_mode: bool = False,
) -> tuple[str, str]:
    final_text = ""
    last_idle_text = ""
    stall = 0
    explore_terminal_streak = 0
    max_stall_exit = get_ide_execution_int("ide_stall_exit_rounds", "INVERST_IDE_STALL_EXIT_ROUNDS", 14)
    explore_warn = get_ide_execution_int(
        "ide_exploration_terminal_streak_warn", "INVERST_IDE_EXPLORATION_TERMINAL_STREAK_WARN", 8
    )
    explore_exit = get_ide_execution_int(
        "ide_exploration_terminal_streak_exit", "INVERST_IDE_EXPLORATION_TERMINAL_STREAK_EXIT", 16
    )
    cap = get_ide_execution_int("tool_result_max_chars", "INVERST_IDE_TOOL_RESULT_MAX_CHARS", 16384)
    coerce_on = _env_int("INVERST_IDE_COERCE_TOOL_CALLS", 1) != 0

    for r in range(max_rounds):
        if verbose:
            print(f"  [ide round {r + 1}/{max_rounds}] {model}...", flush=True)
        msg = llm.chat_completion(messages, tools=tools_spec, model=model, temperature=0.2, timeout=llm_timeout)

        raw = getattr(msg, "content", None) or ""
        if not isinstance(raw, str):
            raw = str(raw) if raw is not None else ""

        raw_tcs = list(getattr(msg, "tool_calls", None) or [])
        coerced = False
        if not raw_tcs and coerce_on:
            raw_tcs = _coerce_parse_tool_calls(raw)
            if raw_tcs:
                coerced = True
                if verbose:
                    print("    [tools] coerced from assistant text (empty tool_calls)", flush=True)

        body = raw.strip()
        if not raw_tcs:
            stall += 1
            final_text = body
            last_idle_text = body
            if _first_line_is_done(body):
                return "success", body
            if stall >= max_stall_exit:
                if verbose:
                    print(
                        f"    [ide] stall exit ({stall} >= {max_stall_exit} rounds without "
                        f"{', '.join(sorted(IDE_STALL_RESET_TOOLS))}; first line must be DONE)",
                        flush=True,
                    )
                return "stalled", (
                    f"[host: safety exit after {stall} idle/weak-tool rounds — run did not complete. "
                    f"Verify `project/outputs/review_gate.md` (completion review), then continue from the same session.]"
                    + (f"\n\n{body}" if body else "")
                )
            if verbose:
                prev = body.replace("\n", " ")[:200]
                print(f"    (no tools; {len(body)} chars) preview: {prev!r}", flush=True)
            messages.append({"role": "assistant", "content": raw})
            nudge = (
                "Use tools: read `SUBTASKS.md` (**Progress** / **Next:** #m), update `[x]` and the Progress line when a step finishes, "
                "then work **only** that module — or when finished reply with **`DONE` alone on the first line** (optional summary after a blank line)."
            )
            if stall >= 2:
                nudge = (
                    "Call **workspace_write** or **terminal_run** for **Next: #m** — reads/search alone do not advance. "
                    "If every line is `[x]`, reply **`DONE`** on the first line."
                )
            if stall >= 5:
                nudge = (
                    f"{stall} rounds without strong tools or DONE — do not alternate `workspace_read` and prose. "
                    f"Either run `{', '.join(sorted(IDE_STALL_RESET_TOOLS))}` for the next task, or first line **`DONE`** if finished."
                )
            messages.append({"role": "user", "content": nudge})
            continue

        tcs = [_tool_call_to_openai_dict(tc, i) for i, tc in enumerate(raw_tcs)]
        tcs = [tc for tc in tcs if tc["function"]["name"]]
        if not tcs:
            if verbose:
                print(
                    "    [ide] tool_calls had no usable function.name (LiteLLM/Ollama object shape?). "
                    "Retrying with explicit tool names.",
                    flush=True,
                )
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Each tool_call must use function.name one of: workspace_read, workspace_grep, workspace_write, "
                        "workspace_list, terminal_run — with valid JSON arguments."
                    ),
                }
            )
            continue

        ok = True
        for tc in tcs:
            fn = _tc_fn(tc)
            a = fn.get("arguments", "{}")
            if isinstance(a, dict):
                a = json.dumps(a, ensure_ascii=False)
            try:
                json.loads(a) if isinstance(a, str) else {}
            except (json.JSONDecodeError, TypeError):
                ok = False
                break
        if not ok:
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": "Tool arguments must be valid JSON string. Retry."})
            continue

        tool_names = [tc["function"]["name"] for tc in tcs]
        if any(n in IDE_STALL_RESET_TOOLS for n in tool_names):
            stall = 0
        else:
            stall += 1
        if stall >= max_stall_exit:
            if verbose:
                print(
                    f"    [ide] stall exit ({stall} >= {max_stall_exit} rounds without "
                    f"{', '.join(sorted(IDE_STALL_RESET_TOOLS))}; first line must be DONE)",
                    flush=True,
                )
            tail = (last_idle_text or body).strip()
            return "stalled", (
                f"[host: safety exit after {stall} idle/weak-tool rounds — run did not complete. "
                f"Verify `project/outputs/review_gate.md` (completion review), then continue from the same session.]"
                + (f"\n\n{tail}" if tail else "")
            )

        asst: dict[str, Any] = {"role": "assistant", "content": "" if coerced else raw, "tool_calls": tcs}
        messages.append(asst)

        hints: list[str] = []
        for tc in tcs:
            fn = _tc_fn(tc)
            name = fn.get("name") if isinstance(fn, dict) else None
            a = fn.get("arguments", "{}")
            if isinstance(a, dict):
                args = a
            else:
                args = json.loads(a) if isinstance(a, str) else {}
            tid = _tc_id(tc)
            impl = tools_impl.get(name) if name else None
            res = impl(**args) if impl else {"status": "rejected", "errors": [{"code": "E_TOOL", "message": name}]}
            if isinstance(res, dict):
                res = _truncate_tool_result(res, max_chars=cap)
            if name == "terminal_run":
                for e in res.get("errors") or []:
                    if e.get("code") == "E_CMD_NOT_ALLOWED" and str((e.get("details") or {}).get("command")) == "cd":
                        hints.append(
                            f"Use terminal_run **cwd** (repo-relative), not cd — e.g. cwd `{outputs_rel}`."
                        )
                        break
            messages.append({"role": "tool", "tool_call_id": tid, "content": json.dumps(res, ensure_ascii=False)})
            if verbose:
                h = json.dumps(res, ensure_ascii=False)[:140]
                print(f"    {name}(...) -> {h}...", flush=True)
        if hints:
            messages.append({"role": "user", "content": "\n".join(dict.fromkeys(hints))})

        if exploration_mode:
            had_write = "workspace_write" in tool_names
            had_terminal = "terminal_run" in tool_names
            if had_write:
                explore_terminal_streak = 0
            elif had_terminal:
                explore_terminal_streak += 1
            if explore_terminal_streak >= explore_exit:
                if verbose:
                    print(
                        f"    [ide] exploration stall exit: {explore_terminal_streak} consecutive terminal_run round(s) "
                        f"without workspace_write (>= {explore_exit}; set INVERST_IDE_EXPLORATION_TERMINAL_STREAK_EXIT to adjust)",
                        flush=True,
                    )
                return "stalled", (
                    "[host: exploration mode — too many consecutive `terminal_run` rounds without `workspace_write` "
                    "to `project/outputs/eda_report.md`. Consolidate findings there, then re-run or continue with DONE.]"
                )
            if explore_terminal_streak >= explore_warn and explore_terminal_streak < explore_exit:
                if explore_terminal_streak == explore_warn or (explore_terminal_streak - explore_warn) % 3 == 0:
                    messages.append({"role": "user", "content": EXPLORATION_TERMINAL_STREAK_NUDGE})

    return "partial", final_text


def run_ide_execution_agent(
    *,
    task: str = "",
    task_mode: str = "override",
    scheme_session_dir: Path,
    workspace_root: Path | None = None,
    model: str | None = None,
    max_rounds: int = 120,
    verbose: bool = True,
    iteration_mode: bool | None = None,
    exploration_mode: bool | None = None,
) -> dict[str, Any]:
    workspace_root = (workspace_root or REPO_ROOT).resolve()
    scheme_session_dir = scheme_session_dir.resolve()
    artifacts_dir = scheme_session_dir / "artifacts"
    explore_on = _resolve_exploration_mode(exploration_mode)
    missing = [n for n in REQUIRED_SCHEME_ARTIFACTS if not (artifacts_dir / n).is_file()]
    if missing and not explore_on:
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_SCHEME", "message": "missing scheme artifacts", "details": {"missing": missing}}],
        }

    outputs_subdir = _ide_outputs_subdir()
    started_at = datetime.now(timezone.utc).isoformat()
    write_scope = get_ide_execution_write_scope()
    allowed = build_allowed_write_prefixes(
        workspace_root=workspace_root,
        scheme_session_dir=scheme_session_dir,
        outputs_subdir=outputs_subdir,
        write_scope=write_scope,
    )
    project_rel = allowed[0]
    outputs_rel = f"{project_rel}/{outputs_subdir}".replace("//", "/")
    implementation_root = (scheme_session_dir / "project").resolve()

    if verbose:
        print(f"  [ide] workspace_root (tool `path` is relative to this): {workspace_root}", flush=True)
        print(f"  [ide] implementation folder (your code lives here): {implementation_root}", flush=True)

    adapter = LocalIDEAdapter(
        workspace_root,
        allowlisted_commands=frozenset(get_ide_execution_command_allowlist()),
        default_timeout_sec=600,
    )
    tools_spec, tools_impl = get_ide_execution_tools(runtime=adapter, allowed_write_prefixes=allowed)

    scheme_max = get_ide_execution_int("scheme_max_chars", "INVERST_IDE_SCHEME_MAX_CHARS", 8000)
    snippets = _scheme_snippets_for_ide(artifacts_dir, scheme_max, exploration_mode=explore_on)

    out_dir = scheme_session_dir / "project" / outputs_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "REPORT_TEMPLATE.md").write_text(_load_execution_report_template(), encoding="utf-8")

    task_stripped = (task or "").strip()
    eda_rel = f"{outputs_rel}/eda_report.md".replace("\\", "/")
    try:
        art_rel = str((scheme_session_dir / "artifacts").resolve().relative_to(workspace_root)).replace("\\", "/")
    except ValueError:
        art_rel = "artifacts"

    repo_tool_prefix = _repo_tool_prefix(workspace_root)

    llm = LLMService()
    m, ide_model_source = resolve_ide_execution_model(model)
    task_for_prompt = task_stripped
    translate_enabled = get_ide_execution_translate_task_enabled()
    task_translate_model = resolve_ide_execution_task_translate_model(m)
    if task_stripped and translate_enabled:
        task_for_prompt = translate_to_english_if_needed(text=task_stripped, model=task_translate_model)
        if verbose and task_for_prompt != task_stripped:
            print(f"  [ide] task translated to English (model={task_translate_model!r})", flush=True)

    tm = (task_mode or "override").strip().lower()
    if tm not in ("override", "supplement"):
        tm = "override"

    iter_on = _resolve_iteration_mode(iteration_mode)

    if explore_on:
        user = _build_exploration_user_message(
            project_rel=project_rel,
            artifacts_rel=art_rel,
            outputs_rel=outputs_rel,
            workspace_root=workspace_root,
            repo_tool_prefix=repo_tool_prefix,
            eda_report_rel=eda_rel,
            scheme_snippets=snippets,
            task_stripped=task_for_prompt,
            task_mode=tm,
        )
    else:
        user = _build_user_message(
            project_rel=project_rel,
            artifacts_rel=art_rel,
            outputs_rel=outputs_rel,
            workspace_root=workspace_root,
            repo_tool_prefix=repo_tool_prefix,
            eda_report_rel=eda_rel,
            scheme_snippets=snippets,
            task_stripped=task_for_prompt,
            task_mode=tm,
            iteration_mode=iter_on,
        )

    timeout = get_ide_execution_int("llm_timeout_seconds", "INVERST_IDE_LLM_TIMEOUT", 900)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": _system_message(
                repo_tool_prefix=repo_tool_prefix,
                iteration_mode=iter_on,
                exploration_mode=explore_on,
            ),
        },
        {"role": "user", "content": user},
    ]

    sk = get_ide_execution_skills_mode()
    skills_inject = "full" if sk in ("full", "1", "true", "yes", "all") else "compact"
    if verbose:
        if task_stripped and tm == "supplement":
            print("  [ide] task_mode=supplement (no Override appendix; supplementary instructions only)", flush=True)
        if iter_on:
            print("  [ide] iteration_mode=on (stale SUBTASKS/DONE ignored until verifiable delta)", flush=True)
        if explore_on:
            print(
                "  [ide] exploration_mode=on (user prompt: exploration mission; scheme snippets may be placeholders)",
                flush=True,
            )
        print(
            f"  [ide] llm.provider={settings.llm.provider!r} default_model={settings.llm.default_model!r} "
            f"run_model={m!r} (source={ide_model_source}) ollama_api_base={settings.llm.ollama.get('api_base', '')!r}",
            flush=True,
        )
        if ide_model_source == "fallback_scheme_phase_default_agent_model":
            print(
                "  [ide] warning: using scheme_phase default model — set ide_execution.coder_model in config/agents.yaml "
                "or INVERST_CODER_MODEL",
                flush=True,
            )
    (out_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "schema_version": "ide_execution_run_v3",
                "implementation": "core/ide_agent.py",
                "started_at": started_at,
                "outputs_subdir": outputs_subdir,
                "llm_provider": settings.llm.provider,
                "llm_settings_default_model": settings.llm.default_model,
                "model": m,
                "ide_coder_model_source": ide_model_source,
                "max_rounds": max_rounds,
                "task_mode": (
                    "supplement"
                    if task_stripped and tm == "supplement"
                    else ("with_override" if task_stripped else "scheme_only")
                ),
                "ide_task_mode_raw": tm,
                "task_original": task_stripped or None,
                "task_for_prompt": task_for_prompt if task_stripped else None,
                "task_translated_to_english": bool(task_stripped and task_for_prompt != task_stripped),
                "iteration_mode": iter_on,
                "exploration_mode": explore_on,
                "translate_task_enabled": translate_enabled,
                "task_translate_model": task_translate_model if task_stripped else None,
                "ide_skills_inject": skills_inject,
                "scheme_snippet_max_chars": scheme_max,
                "ide_core_rules_path": str(IDE_CORE_RULES_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                "ide_rules_profile": get_ide_execution_ide_rules_profile(),
                "ide_core_rules_max_chars": get_ide_execution_int(
                    "ide_core_rules_max_chars", "INVERST_IDE_CORE_RULES_MAX_CHARS", 12000
                ),
                "ide_rules_path": str(IDE_RULES_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                "ide_rules_max_chars": get_ide_execution_int("ide_rules_max_chars", "INVERST_IDE_RULES_MAX_CHARS", 32000),
                "note": "v3: default ide_core_rules.md (+ optional extended ide_execution_rules.md); no timestamp dirs; started_at only",
                "eda_report_rel": eda_rel,
                "ide_tool_result_max_chars": get_ide_execution_int(
                    "tool_result_max_chars", "INVERST_IDE_TOOL_RESULT_MAX_CHARS", 16384
                ),
                "ide_artifact_read_max_chars": get_ide_execution_int(
                    "artifact_read_max_chars", "INVERST_IDE_ARTIFACT_READ_MAX_CHARS", 98304
                ),
                "ide_llm_timeout_seconds": timeout,
                "ollama_api_base": settings.llm.ollama.get("api_base", ""),
                "allowed_write_prefixes": list(allowed),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        status, final_text = _tool_loop(
            llm=llm,
            model=m,
            messages=messages,
            tools_spec=tools_spec,
            tools_impl=tools_impl,
            max_rounds=max_rounds,
            llm_timeout=timeout,
            verbose=verbose,
            outputs_rel=outputs_rel,
            exploration_mode=explore_on,
        )
    except LLMCompletionError as e:
        if verbose:
            print(f"  [ide] LLM failure (aborting run): {e}", flush=True)
        out_base = scheme_session_dir / "project" / outputs_subdir
        (out_base / "llm_error.txt").write_text(str(e), encoding="utf-8")
        return {
            "status": "rejected",
            "workspace_root": str(workspace_root),
            "scheme_session_dir": str(scheme_session_dir),
            "implementation_root": str(implementation_root),
            "outputs_dir": str(out_base),
            "outputs_subdir": outputs_subdir,
            "project_dir": str(scheme_session_dir / "project"),
            "started_at": started_at,
            "model": m,
            "final": "",
            "eda_report_rel": eda_rel,
            "worklog_rel": f"{project_rel}/WORKLOG.md".replace("\\", "/"),
            "ide_memory_rel": f"{project_rel}/IDE_MEMORY.md".replace("\\", "/"),
            "allowed_write_prefixes": list(allowed),
            "errors": [{"code": "E_LLM", "message": str(e)}],
        }

    out = scheme_session_dir / "project" / outputs_subdir / "final_assistant.txt"
    out.write_text(final_text or "", encoding="utf-8")

    wl = f"{project_rel}/WORKLOG.md".replace("\\", "/")
    mem = f"{project_rel}/IDE_MEMORY.md".replace("\\", "/")
    return {
        "status": status,
        "workspace_root": str(workspace_root),
        "scheme_session_dir": str(scheme_session_dir),
        "implementation_root": str(implementation_root),
        "outputs_dir": str(scheme_session_dir / "project" / outputs_subdir),
        "outputs_subdir": outputs_subdir,
        "project_dir": str(scheme_session_dir / "project"),
        "started_at": started_at,
        "model": m,
        "final": final_text,
        "eda_report_rel": eda_rel,
        "worklog_rel": wl,
        "ide_memory_rel": mem,
        "allowed_write_prefixes": list(allowed),
    }
