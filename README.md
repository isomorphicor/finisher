# Inverst Agent (Research-First Quant Stack)

[中文说明](README.zh-CN.md)
[快速使用说明](quick_setup_zh.md)

**Design goal:** Agents that **replace humans** at the **frontier of knowledge** — freely exploring and delivering high-level research. They are **power users of open-source tools** (Cursor, Trae, Aider, MCP, etc.), not rebuilders of them, and they are built for **deep thinking**: framing questions, debating approaches, judging evidence. Current runnable focus is the scheme phase; see [scheme phase blueprint](docs/experiments/scheme_phase/blueprint.md).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## What is Inverst Agent?

Inverst Agent is **CIO-led** (see `docs/policies/cio.md`): one orchestrating thread turns intent into blueprints and acceptance evidence—aligned with **single-operator** quant work (full stack, no fake departmental walls). **Implementation** routes through **MD policy skills** registered in `docs/skills/manifest.json` (e.g. data-scientist, quant-researcher, quant-dev, quant-soul) as **contracts**, not as separate “department” agents. Policies, `docs/reference/quant_tech_stack.md`, and `knowledge/` supply methodology and technique; optional **Layer 1 / Layer 2 / Reviewer** labels in `docs/agent/AGENTS.md` are shorthand only. Execution leans on **open-source tools and external agents** (e.g. Cursor/Trae). Core loop: **mandate → evidence → gates → sign-off.**

## Key Features

*   **Literature Review:** Searches Arxiv to support or refute hypotheses.
*   **Deterministic Experiments:** Runs reproducible experiments with explicit assumptions.
*   **Evidence Gates:** Time-safety and validation requirements are enforced as acceptance criteria.
*   **Skill-First Extensibility:** Deterministic `BaseSkill` tools plus **MD policy skills** in [`docs/skills/manifest.json`](docs/skills/manifest.json) (CIO, quant-soul, data-scientist, quant-researcher, quant-dev)—**contracts for stages**, not separate “department” agents.

## Quick Start

### 1. Installation
```bash
git clone https://github.com/isomorphicor/finisher.git
cd finisher
pip install -r requirements.txt
```

### 2. Configure (Optional)
- `config/settings.yaml` — API keys / backend preferences.
- `config/agents.yaml` — scheme phase: `scheme_phase.default_agent_model` (main tool-loop LLM), `reviewers`, `translator`. Override per run with `python scripts/run_scheme_agent.py --model ...` or env `INVERST_SCHEME_AGENT_MODEL`.

### 3. Command examples

Session layout: `<runs_root>/<project>/<session>/` — e.g. `~/Project/projects_generated/algo_alpha/main`. In-repo default: `out/<project>/<session>/`. Artifacts under `artifacts/`, code under `project/src/`, run outputs under `project/outputs/`. **`--project`** and **`--session`** are the two path segments (default session name `main` unless `INVERST_DEFAULT_SCHEME_SESSION` is set or `timestamp`). More examples: [`docs/guides/command_examples.md`](docs/guides/command_examples.md).

**One-shot — scheme, execution prep, and IDE coding in one process (recommended):**

```bash
python scripts/run_research_session.py --project algo_alpha --ide-max-rounds 200 \
  "Your research task for the scheme phase"
```

Equivalent legacy name: `python scripts/run_scheme_then_ide.py` (same pipeline via `core/research_session_pipeline.py`). Optional: `--ide-task "…"` (extra instruction for the IDE step only), `--skip-execution-prep`, `--abort-ide-on-scheme-partial`. See `--help` on either script.

**Deprecated:** `scripts/run_autonomy_loop.py` — use `run_research_session.py` or `run_scheme_then_ide.py` instead; see [`docs/skills/ARCHITECTURE.md`](docs/skills/ARCHITECTURE.md).

Skill layering (policy / ops / runtime): [`docs/skills/ARCHITECTURE.md`](docs/skills/ARCHITECTURE.md).

**Smoke test (plan + code in one run):** [`docs/experiments/smoke_plan_and_code.md`](docs/experiments/smoke_plan_and_code.md) — `./scripts/smoke_research_session.sh` (requires LLM backend).

If the scheme phase stops before writing all four `artifacts/*.md`, the combined run exits with a JSON field `scheme_artifacts_missing` — raise `--scheme-max-rounds` or re-run `run_scheme_agent` on the same session.

**Step by step — same pipeline, three commands:**

```bash
python scripts/run_scheme_agent.py --project algo_alpha "Your research task"
python scripts/run_execution_prep.py --project algo_alpha --resume-latest --workspace-root .
python scripts/run_ide_execution_agent.py "out/algo_alpha/$(cat out/algo_alpha/LATEST)" \
  --workspace-root . --max-rounds 200
```

(Use straight quotes; put a space between `--max-rounds` and `200`.)

**Utilities (skills / tools):**

- `python scripts/run_routed_tool.py --intent workspace.write --args-json '{"path":"demo.txt","content":"hello"}'`
- `python scripts/install_skill.py <path_to_skill_package>`
- `python scripts/list_skills.py --capability workspace.write`
- `python scripts/create_skill_template.py my_skill --output-dir /tmp`

Suggested skill flow: `create_skill_template` → edit `runtime.py` → `install_skill` → `run_routed_tool`.

## Documentation

*   [**Docs Index**](docs/README.md): Start page for contracts and standards.
*   [**Project Status**](docs/project_status.md): Current roadmap and active tasks.
*   [**Worklog**](docs/worklog.md): Minimal change log (only key behavior changes).
*   [**Skill Catalog**](docs/guides/skill_catalog.md): List of available Python tools (Skills).
*   [**Coding Conventions**](docs/guides/coding_conventions.md): Guidelines for contributing code.
*   [**Module Contracts**](docs/contracts/module_contracts.md): Module boundaries, IO, evidence artifacts.
*   [**Research Standards**](docs/contracts/research_standards.md): Acceptance gates and evidence standards.

Legacy notes:

## Roadmap
*   [x] Execution scaffolding MVP: consume scheme artifacts and generate IDE checklist/workspace
*   [x] Skill registry + intent router for install/discover/on-demand invocation
*   [x] Runtime abstraction with Local/MCP-compatible backend interface

## License
MIT
