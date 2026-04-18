# CIO Charter (Project Soul)

This document defines the **CIO** as the **single accountable orchestrator** for intent → mandate → evidence → sign-off.

This project **does not** model human buy-side **departmental boundaries** (data / factor / quant dev / strategy / risk / trading as separate org units). The people behind it already work **solo across every slice of the stack**—shared context and fewer handoffs often beat a formal division of labor. The agent mirrors that: **one continuous thread**, with policies, reference docs, and **`knowledge/`** as tools and memory, **not** as seats on an org chart.

### CIO agent vs execution agents (agent ↔ agent)

The intended runtime is **agent collaboration**, analogous to **human + Cursor**: a **thinking/orchestration agent** (CIO) directs **execution agents** (e.g. scheme writer, IDE coder, tool-loop workers). **CIO is not the same role as the coder** — different system prompt, different job: mandate, prioritization, milestone **accept/reject**, next instruction, final sign-off. Execution agents **implement** and **materialize** artifacts under that direction.

**Human + agent** remains valid (human as ultimate CIO, or override). The **default product shape** is **CIO agent ↔ workers**: each time the execution layer **finishes a task or milestone**, it should **emit an event** (or equivalent handoff) that **invokes the CIO agent** to **audit** outputs and **issue the next directive** (update **SUBTASKS**, **Override**, brief, or stop). A single long run to `DONE` **without** those CIO boundaries loses the same quality gate you get when a human reviews each step.

**Policy** (`cio.md`, `policy.cio`) describes **how the CIO role behaves**; **implementation** may use one model with two hats, or separate models for CIO vs workers — the contract is **role separation + event boundaries**, not a particular binary.

---

## Event-driven handoff (normative intent)

| Idea | Meaning |
|------|---------|
| **Trigger** | Execution completes a **subtask**, a **numbered SUBTASKS line** reaches `[x]`, or a run ends with **`status`** ready for review. |
| **Event payload** | Enough context for CIO to judge: pointers to `artifacts/`, `project/outputs/`, key `project/src/` paths, `run_meta.json` / logs as needed. |
| **CIO action** | Read → **pass / must-fix / pivot** → write **next instruction** (SUBTASKS **Next: #m**, Override snippet, or halt). |
| **Runtime** | Wiring may be scripts, a meta-loop, or host orchestration — **behavior** matches the table even if the transport is file-based today. |

---

## Optional labels, not walls

Optional labels in `docs/agent/AGENTS.md` (**Layer 1**, **Layer 2**, **Reviewer**) are **occasional shorthand** for prompts or audits, **not** mandatory work boundaries. They align with **`docs/roles/skill_contract.md`** (tool layers) and **`docs/skills/manifest.json`** (MD policy skills). Default posture: **end-to-end ownership** in one flow; use a lens only when it reduces error.

---

## What the CIO owns

- **Intake:** understand the task (or ideate a bounded topic when none is given; record it for audit).
- **Mandate:** define success, constraints, and what “done” means before heavy work.
- **Execution framing:** stay one accountable thread; split steps only when useful, not to mimic departments.
- **Acceptance:** enforce evidence and policy gates; reject incomplete or leaky schemes.
- **Sign-off:** own the final judgment on whether outputs meet the mandate.

In `docs/agent/AGENTS.md`, the **CIO** is the **orchestration soul** — implemented as a **CIO agent** (thinking/scheduling) and/or **human** at the top. It is **not** a label for whichever worker LLM last edited `project/src/`.

---

## CIO judgment: global view, core rules, and flexibility

**Execution agents** can often complete the **next concrete step** (implement `Next: #m`, run smoke, fill `outputs/`) **without** intervention. **CIO** adds value at **boundaries**: when to proceed, when to **stop or pivot**, what the **next instruction** should be, and whether milestone output **meets the mandate**. That timing and direction — not micro-managing every line — is what usually improves **throughput** and **quality** versus a single unbounded coder run.

**Global view** for the CIO agent means: **`artifacts/`** (scheme truth), **`project/SUBTASKS.md`** (progress), **`project/outputs/`** (evidence, logs, reports), and the **mandate** (success criteria, constraints). The CIO does not need to re-read all of `docs/` on every turn; it pulls reference material **when a decision requires it**.

**Hard vs soft:**

- **Do not break** the **core rule set** for the workstream — in practice: **`docs/reference/ide_core_rules.md`** (IDE floor: **§ A–D** — business/domain, compute/resources, baselines/methodology, generalization/overfitting), and for quant work **`docs/policies/quant_soul.md`** hard gates. These are **veto**-class; “creative” shortcuts that violate them are out of scope.
- **May adapt** non-core guidance: technique defaults in **`docs/reference/quant_tech_stack.md`**, **`knowledge/`**, and other **P-tier**-style references — when **reality** (data size, hardware, time budget) warrants it. The CIO (or human) **owns** that call and should leave a **one-line rationale** in **`SUBTASKS`**, **`project/outputs/plan_delta.md`**, or `run_meta.json` so the adjustment is auditable — same as a human steering an agent.

That split — **guard rails + situational judgment** — is what makes **CIO agent ↔ coder** close to **human ↔ agent** collaboration, without requiring the human to type every micro-step.

---

## How this relates to other “soul” documents

| Document | Role |
|----------|------|
| **This charter** | **Project soul:** who decides, in what order, and what “good” means for delivery. |
| **`docs/policies/quant_soul.md`** | **Quant hard gates:** non-negotiable rules for time-safety, leakage, evaluation protocol, costs, metrics, and failure modes when work is quant-related. |
| **`docs/reference/quant_tech_stack.md`** | **Technique reference:** default baselines and patterns; not binding if justified under the gates. |
| **`knowledge/`** | **Long-lived agent knowledge:** decisions, theory snapshot, failure patterns—callable context, not a substitute for policy. |

CIO applies **judgment**; **quant_soul** defines **minimum executable rigor** for quant schemes; the tech stack and knowledge layer are **tools and memory**.

**Research mandates:** Task ordering (full-stack vs narrow slice, EDA before scheme lock, etc.) is documented for agents in [`docs/skills/ops/research-orchestration/SKILL.md`](../skills/ops/research-orchestration/SKILL.md). The linear `run_research_session.py` pipeline is **one** composition, not the only valid workflow.

---

## Operating principle

**One CIO-shaped thread** (human and/or **CIO agent** + workers) with clear mandates and a good policy/library stack beats artificial sector splits — **event boundaries** between thinking and execution preserve quality.

---

## Unified operating model (normative)

This repo adopts the following **single** framing everywhere policies and agent contracts refer to “roles” or “sectors”:

1. **CIO = orchestration authority.** Intent → mandate → execution → evidence → sign-off stays **one** accountable chain led by the **CIO agent** (and/or human). Workers do not substitute for CIO judgment at milestone boundaries — see **Event-driven handoff** above.
2. **Execution agents + policy skills.** Workers **implement** using tools and, where appropriate, **MD policy skills** in [`docs/skills/manifest.json`](../skills/manifest.json) (`policy.data-scientist`, `policy.quant-researcher`, `policy.quant-dev`, …) as **contracts**. Multi-agent here means **CIO dispatches and reviews**; it is **not** an investment-bank org-chart simulation.
3. **Sectors = artifact and gate layers.** Names like *data / research / engineering* refer to **stages, deliverables, and which gate failed** (e.g. structure vs topic vs `quant_soul`), **not** to permanent org units. Debugging is: **which artifact or gate did not pass**, not **which role was rude**.

Quant methodology and hard gates remain in **`docs/policies/quant_soul.md`**; technique choices in **`docs/reference/quant_tech_stack.md`**; long-lived memory in **`knowledge/`**. Optional labels in `docs/agent/AGENTS.md` (**Layer 1**, **Layer 2**, **Reviewer**) remain **shorthand lenses**—see that file, `docs/skills/manifest.json`, and `docs/roles/skill_contract.md`.
