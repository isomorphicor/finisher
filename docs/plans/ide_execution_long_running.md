# Plan: Long-Running IDE Execution Agent (Post-Experiment)

**Status:** Draft — execute **after** the current experimental phase stabilizes.  
**Scope:** Extend `run_ide_execution_agent` / `core/ide_agent.py` from bounded multi-round runs to **resumable, hours-to-days** sessions without relying on a single long-lived process.

**Related:** `docs/skills/ops/data-first-execution/SKILL.md` (sub-tasks, EDA-first), `runtime/adapters/local_adapter.py` (tools). **Orchestration soul:** `docs/policies/cio.md` (CIO agent ↔ execution agents, event handoff). **Local inference:** `docs/guides/ide_context_budget.md` (Ollama idle unload, same-model concurrency).

---

## 1. Goals

| Goal | Success criteria |
|------|------------------|
| **Resumability** | Stop the process anytime; restart and continue without re-doing completed work from scratch. |
| **Bounded context** | Conversation + tool history does not grow without limit over days. |
| **Long jobs** | Terminal steps that run for hours are **tracked** (log path, job id), not “silent” hangs. |
| **Operability** | Clear files under `project/` (`src/`, `outputs/`, etc.) are the **source of truth** for humans and agents. |

Non-goals for v1: fully unattended multi-day runs with no budget; replacing human review for expensive steps.

---

## 2. Current baseline (as of experiment phase)

- Single Python process, **`max_rounds`** cap, in-memory **`messages`** list.
- State on disk: code under **`out/.../<project>/<session>/project/`**, optional **`SUBTASKS.md`**, run artifacts under **`project/outputs/`** (stable path; invocation time in `run_meta.json` only).
- No checkpoint of LLM thread; restarting loses chat context (files remain).

---

## 3. Phased roadmap

### Phase A — Checkpoint + resume (highest priority)

**Deliverables**

- **Checkpoint file** (e.g. `project/outputs/checkpoint.json` or `project/agent_checkpoint.json`) storing at minimum:
  - `schema_version`, `started_at`, `last_round`, `model`, `max_rounds` used
  - **Compressed state**: last N user/assistant turns **or** a rolling **summary** string
  - Pointer to `SUBTASKS.md` / evidence paths
- CLI: **`--resume`** path **or** **`--continue-last`** (find latest checkpoint under session `project/`).
- On resume: inject a short system/user block: “Resuming from round R; completed sub-tasks: …” (read from `SUBTASKS.md` if present).

**Acceptance**

- Kill process mid-run; restart with `--resume`; agent continues without rewriting entire codebase blindly.

### Phase B — Context window management

**Deliverables**

- After every K rounds (configurable), **append** a round summary to **`project/SESSION_LOG.md`** (or under `project/outputs/`).
- Trim or replace old `messages` with: fixed system + **summary block** + last M tool-heavy turns only.
- Optional: env **`INVERST_IDE_EXEC_MAX_MESSAGE_TURNS`** (default e.g. 30).

**Acceptance**

- Long sessions do not OOM or exceed model context due to chat history alone.

### Phase C — Long-running terminal jobs

**Deliverables**

- Document pattern: **`nohup`** / job script + log file under `project/outputs/`, agent records **PID / log path** in checkpoint or markdown.
- Optionally extend **`terminal_run`** result schema in docs (not necessarily code) for “detached” runs.
- Clarify **`timeout_sec`** strategy: large timeouts only when user/agent explicitly opts in.

**Acceptance**

- Multi-hour training jobs do not block the supervisor loop without traceability.

### Phase D — Supervisor (optional wrapper)

**Deliverables**

- **Prototype:** `scripts/run_supervisor_ide.py` + `core/supervisor_ide_loop.py` — chunked IDE + text-only CIO rounds (provider via `settings.llm` + `resolve_supervisor_cio_model`); **no** checkpoint resume yet. Same file set references Phase F handshake ideas (`cio_directive_latest.json`).
- Script e.g. **`scripts/supervise_ide_execution_agent.py`**: loop invoking `run_ide_execution_agent` with **`--max-rounds`** chunks + **`--resume`**, global **`--max-total-rounds`** or **deadline**, sleep between chunks.
- Exit when assistant returns **DONE** or budget exhausted.

**Acceptance**

- Cron/systemd can drive multi-hour **staged** runs without one giant process.

### Phase E — Human gates (optional)

**Deliverables**

- Convention: agent writes **`PAUSED.md`** in evidence when blocked; human edits **`SUBTASKS.md`** or removes pause file to continue.
- Or: `--require-approval-file` before certain tool classes (later).

### Phase F — CIO orchestration layer (agent ↔ agent)

**Motivation:** Bounded `max_rounds` IDE runs lack a **thinking** supervisor that re-reads `artifacts/` + `project/outputs/` between milestones. Product intent: **CIO agent** directs **execution agents**; **events** wake CIO after each subtask or when long work finishes (`docs/policies/cio.md` **Event-driven handoff**).

**Deliverables**

- **Wrapper script** (e.g. `scripts/run_ide_cio_loop.py` or extend supervisor): after each **chunk** of `run_ide_execution_agent` (or after a **milestone** file appears under `project/outputs/`), run a **CIO round** — read-only + write **`SUBTASKS.md` / `project/outputs/cio_directive.md`** (or equivalent), then spawn the next execution chunk with updated user task / Override.
- **Handshake files:** e.g. `project/outputs/milestone_complete.json` (written by execution layer or wrapper) → CIO consumes → emits next instruction.
- **Long training / hours-long jobs:** execution records **PID, log path, ETA** (Phase C); **CIO loop sleeps** or exits until **`training_complete`** / file watcher / cron — no busy-wait on GPU.
- **Optional:** lightweight **heartbeat** (separate from events) if no output for **T** minutes — CIO only checks `SUBTASKS` + last log line (cheap).

**Acceptance**

- Same session can run as **staged** IDE invocations with **explicit CIO boundaries**, without requiring one infinite `max_rounds` process.

### Phase G — Local inference scheduling (Ollama)

**Motivation:** Large RAM/VRAM allows **several models** loaded, but **two concurrent heavy requests on the same model name** hurt throughput (Ollama multiplexes one loaded copy). Idle unload reloads weights after gaps.

**Deliverables**

- **Document + config convention:** **one logical queue per Ollama model tag** (serialize CIO vs coder if they share one tag); **parallel lanes** use **different model names** (e.g. small orchestrator + large coder).
- **Optional env** in wrapper: `INVERST_CIO_MODEL` vs `INVERST_IDE_CODER_MODEL` (names illustrative) so orchestration and coding never stampede the same tag.
- Wire **`keep_alive`** / batching policy where the **resident** supervisor pings Ollama (see `docs/guides/ide_context_budget.md`).

**Acceptance**

- No documented expectation that **same model** serves **two** long parallel chats at **2×** speed; ops knows to **split tags** or **queue**.

### Phase H — Reviewer-only round (process + optional automation)

**Motivation:** Execution agent optimizes for “done”; a **read-only** pass (or the same model with a reviewer system prompt) enforces **R-line** metrics / leakage / **tradable return vs label** before expensive training **and** before **`DONE`** on portfolio claims (complements CIO, can share the same small model).

**Normative in repo:** **`docs/templates/ide_review_gate.md`** → **`project/outputs/review_gate.md`** — required whenever the session claims **Sharpe / CPCV acceptance / portfolio** results (`ide_core_rules.md` Workflow, `ide_execution_rules.md` step 6).

**Deliverables**

- **Artifact:** markdown **pass / must_fix** + bullets (template above). Optional JSON mirror: **`project/outputs/review_gate.json`**.
- Script or mode: **no `workspace_write` to `src/`** — input = `artifacts/` + `outputs/` + selected `src/` paths; output = review gate file(s).
- Optional hook: supervisor **refuses** next training chunk if **must_fix** non-empty (human override flag).

**Acceptance**

- One command (or manual step) produces a **structured** review artifact suitable for SUBTASKS or CIO consumption; aligns with Workflow step 6.

---

## 4. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Checkpoint stale vs edited files | Prefer **file-based truth** (`SUBTASKS`, code); checkpoint only carries **summary + pointers**. |
| Summary drift | Periodic “re-read `SUBTASKS.md` and top of `SESSION_LOG.md`” in system prompt on resume. |
| Security of `terminal_run` in long runs | Keep allowlist; document that supervisor runs under same user; no broadening without review. |
| CIO + IDE **race** on same files | Serialize via wrapper; single writer to `SUBTASKS` / directive file per step. |
| Ollama **VRAM** fragmentation with many tags | Cap concurrent model tags; document “2–3 models max” ops pattern. |

---

## 5. Open decisions (decide before implementation)

- Single global checkpoint per session vs separate checkpoints under **`project/outputs/`** (or a dated copy the human creates).
- Whether **resume** overwrites **`outputs/`** or writes to a user-copied directory (git / manual snapshot for versioning).
- Default **K** (rounds between summaries) and **M** (turns retained verbatim).
- **CIO wrapper:** single process vs **cron**-driven “wake CIO” only (lighter, but coarser events).
- **Reviewer vs CIO:** one small model with two system prompts vs two model tags.

---

## 6. Suggested order of work

1. **Phase A** (checkpoint + resume) — unblocks everything else.  
2. **Phase G** (inference scheduling doc + queue convention) — cheap; avoids wrong parallelism assumptions while building F.  
3. **Phase F** (CIO orchestration wrapper + milestone files) — product shape for agent↔agent; can use **staged** Phase D before full checkpoint story.  
4. **Phase B** — required before “days” of wall time in a **single** long `messages` buffer.  
5. **Phase C** — as soon as real jobs exceed ~30 minutes.  
6. **Phase D** — unattended chaining of chunks (pairs naturally with F).  
7. **Phase E** — if mandate requires human sign-off between stages.  
8. **Phase H** — review gate aligned with **`review_gate.md`**; optional automation for read-only reviewer pass before heavy spend.

---

## 7. References in repo

- `core/ide_agent.py` — tool loop, `run_meta.json`, evidence paths.  
- `scripts/run_ide_execution_agent.py` — CLI entry.  
- `docs/skills/ops/data-first-execution/SKILL.md` — sub-task decomposition, iterative workflow.  
- `docs/policies/cio.md` — CIO agent vs execution agents; **Event-driven handoff**.  
- `docs/reference/ide_core_rules.md` — default IDE rules embedded in agent.  
- `docs/guides/ide_context_budget.md` — Ollama idle unload, same-model concurrency, keep-alive notes.
