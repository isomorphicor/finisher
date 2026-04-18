# Core principles (terse) vs knowledge base (depth)

**Why:** Agents and humans should **scan principles first** (short, non-negotiable or high-priority). Anything that needs derivation, alternatives, or case law lives in the **knowledge base** — linked, not copied in full into every skill.

| Layer | Role | Typical length |
|-------|------|----------------|
| **Principles** (this page + linked one-pagers) | What we **always** remember in one pass | Bullets, no prose walls |
| **Policies** | Enforceable contracts | `docs/policies/*.md` — still structured, not tutorials |
| **Knowledge base** | Reference, nuance, promoted lessons | `knowledge/*.md`, `docs/reference/*`, deep guides |

Add new **principle** lines only when they are stable; add **detail** beside them as links to KB or policy sections.

### Orchestration & deliverables

1. **Mandate + resources → agent-planned work** — User states intent and supplies means (data, budget, APIs); **decomposition** into phases/skills is the agent’s job unless explicitly fixed. → [`docs/skills/ops/research-orchestration/SKILL.md`](../skills/ops/research-orchestration/SKILL.md)  
2. **Conclusions over code review** — Primary success is **research conclusions** usable for decisions (**evidence**, **limitations**, reproducibility). Code supports **re-run**, not default human line-by-line audit. → [`docs/templates/research_report.md`](../templates/research_report.md), [`ide_core_rules`](../reference/ide_core_rules.md) *Accountability*  
3. **Adaptive phase order** — Not fixed to scheme-first; depends on mandate. → [`research-orchestration`](../skills/ops/research-orchestration/SKILL.md)  
4. **Resource transparency** — Missing tools/data documented as explicit **requests** for user approval; no silent assumption of browser/vendor access.

---

## Quant & execution (headlines)

1. **Time-safety** — decision-time information set; no lookahead; timestamps explicit. → [`docs/policies/quant_soul.md`](../policies/quant_soul.md) §1–2  
2. **Acceptance evidence** — default **CPCV-class** path multiplicity + diagnostics; alternatives allowed if **same burden of proof** on overfitting. → `quant_soul` §3  
3. **Not for acceptance / production gating** — **walk-forward / forward rolling** as primary supervised evidence. → `quant_soul` §3  
4. **Short validity horizons** — do not rely on “live months” alone as proof. → `quant_soul` §3 burden-of-proof bullet  
5. **RL** — train in **sim/synthetic** when useful; production when **real-data inference/execution** is **stable** under explicit eval. → `quant_soul` §3 RL + [`docs/reference/quant_tech_stack.md`](../reference/quant_tech_stack.md) § RL / Control  
6. **Exploration vs acceptance** — simple time-safe splits for HPO; **no** CPCV combinatorics for exploration. → `quant_soul` §3, [`ide_execution_rules.md`](../reference/ide_execution_rules.md)  
7. **Experiment economics** — probe → lock direction → scale; cost–benefit each step. → [`docs/skills/ops/cognitive-research-flow/SKILL.md`](../skills/ops/cognitive-research-flow/SKILL.md)  
8. **IDE session** — data-first, baselines before heavy grids, honest portfolio metrics. → [`ide_core_rules.md`](../reference/ide_core_rules.md)  
9. **No silent drops** — do not skip **any** mandated link (scheme, validation, returns, review gate, …). Over budget → **solve** (shrink scope, HPC, stage); or **document** deferral in `outputs/`. **Multi-target vs per-label** — **probe** first, not assumed. → [`cognitive-research-flow`](../skills/ops/cognitive-research-flow/SKILL.md)  

CIO / orchestration: [`docs/policies/cio.md`](../policies/cio.md).

---

## Where the long text lives

| Topic | Knowledge / reference |
|-------|------------------------|
| Full quant gates & acceptance language | [`docs/policies/quant_soul.md`](../policies/quant_soul.md) |
| Models, NN/GBDT habits, RL detail | [`docs/reference/quant_tech_stack.md`](../reference/quant_tech_stack.md) |
| IDE tiers, combinatorics, Override | [`docs/reference/ide_execution_rules.md`](../reference/ide_execution_rules.md) |
| Promoted session lessons (append-only) | [`knowledge/README.md`](../../knowledge/README.md) (repo root `knowledge/`) |
| Skill registry & layers | [`docs/skills/ARCHITECTURE.md`](../skills/ARCHITECTURE.md), [`manifest.json`](../skills/manifest.json) |

**Rule of thumb:** If a new idea needs more than **~5 lines** to state clearly, put the **headline** here (or in the relevant policy) and **move the essay** to `knowledge/` or `docs/reference/` and link it.
