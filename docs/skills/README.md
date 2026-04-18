# Skills — start here

This page is the **entry point** for humans and agents before diving into policy lenses, ops playbooks, and runtime CLIs.

## Mission

**User** states **mandate** (research question, constraints) and supplies **resources** (data paths, compute, APIs, budget). **Agent** **plans and executes** work autonomously and must deliver **decision-grade outputs**: conclusions tied to **reproducible evidence**, explicit **limitations**, and honest **uncertainty** — not “please review my source code.” Code exists for **reproduction**; it is not the primary review artifact. See [`docs/reference/ide_core_rules.md`](../reference/ide_core_rules.md) (*Accountability*) and [`docs/principles/README.md`](../principles/README.md).

## Capabilities vs responsibilities

| | |
|--|--|
| **Within tools** | Read/write under the session `project/`, allowlisted `terminal_run`, literature search where exposed (scheme phase today; IDE extension planned). |
| **Must deliver** | Written conclusions, metrics paths, commands that match runs, and (when claiming quant acceptance) compliance with [`docs/policies/quant_soul.md`](../policies/quant_soul.md). |
| **May request** | Missing **tools or data** the user must approve — e.g. `project/outputs/resource_requests.md` (browser automation, vendor purchase, extra compute). No silent assumption those exist. |

## Skill catalog (“menu”)

- **Registry:** [`manifest.json`](manifest.json) — stable `id`s (`policy.*`, `ops.*`).
- **Layers:** [`ARCHITECTURE.md`](ARCHITECTURE.md) — L0 policy, L1 ops, L2 runtime, L3 meta.
- **Orchestration:** [`ops/research-orchestration/SKILL.md`](ops/research-orchestration/SKILL.md) — how to choose **phase order** and **stopping rules** (full-stack vs narrow mandate); **linear** `run_research_session.py` is **one** composition, not the only valid workflow.
- **Manual supervisor (Phase 3b):** [`ops/manual-supervisor-playbook/SKILL.md`](ops/manual-supervisor-playbook/SKILL.md) — compose **L2** entrypoints stepwise when you are not using the all-in-one CLI.
- **Information collection:** [`ops/information-collection/SKILL.md`](ops/information-collection/SKILL.md) — literature / paper search and extension points ([`core/paper_search.py`](../../core/paper_search.py)).
- **Credible report shape:** [`templates/research_report.md`](../templates/research_report.md) — executive answer + evidence appendix + limitations + repro bundle.

## Related

- [`docs/policies/cio.md`](../policies/cio.md) — mandate ownership vs execution.
- [`docs/skills/ops/cognitive-research-flow/SKILL.md`](ops/cognitive-research-flow/SKILL.md) — probe → commit → scale under constraints.
