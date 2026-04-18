# IDE execution agent — context budget

Implementation: **`core/ide_agent.py`** (v2). Older docs referred to chat compression modules — **v2 removed** in-process history folding/shrink; only **per-tool JSON truncation** remains.

## Token sources

| Piece | Notes |
|-------|--------|
| System + skills | **Default `skills_inject: compact`** (short hints + link to SKILL docs). Set **`INVERST_IDE_SKILLS=full`** to embed full SKILL.md bodies when upgrading capability. |
| User msg: 4 scheme files | **4 ×** `scheme_max_chars` from yaml (default **8000** for core runs). Raise `INVERST_IDE_SCHEME_MAX_CHARS` if snippets truncate too much. |
| Report template | On disk only: `REPORT_TEMPLATE.md` under the run’s evidence dir. |

## Defaults (`config/agents.yaml` → `ide_execution:`)

Env vars **`INVERST_*`** override each key when set.

- **`tool_result_max_chars`** — cap each **tool** message JSON (default **16384**).
- **`artifact_read_max_chars`** — higher cap for paths under **`…/artifacts/`** (default **98304**).
- **`scheme_max_chars`**, **`llm_timeout_seconds`**, **`skills_inject`** — see yaml.

## v2 behavior (no chat compression)

- The runner **does not** rewrite or fold prior turns. Long sessions depend on the model’s **context window**; split work across runs if needed.
- **Ollama quirk:** if the API returns empty `tool_calls` but the assistant body is JSON tool calls, set **`INVERST_IDE_COERCE_TOOL_CALLS=1`** (default) so the host still executes tools.

## Local inference (Ollama) — idle unload

Ollama **unloads** a model after **idle** time to free VRAM/RAM. The next request may pay **load + first token** latency again (worse for **larger** models). This is independent of IDE context size — it is **runtime policy** on the server.

**Implications for CIO / event loops:** long gaps between “wake CIO” calls can look like **cold starts** even though you use the same model name.

**Mitigations (pick what fits):**

- **Batch** CIO reviews so idle gaps are shorter than the unload window, or **accept** reload cost between sessions.
- **Smaller / faster model** for frequent orchestration turns; reserve the **large** weights for heavy coding or training-adjacent steps.
- **Keep-alive:** Ollama’s API supports a **`keep_alive`** parameter on chat/generate requests; the server also has knobs for how long weights stay resident — see current **Ollama** docs for defaults and env/server flags (they change across versions).
- **One long-lived client session** (same HTTP connection to a **running** `ollama serve`) avoids *process* restart cost; it does **not** by itself prevent **weight** unload after idle — that is still governed by server keep-alive behavior above.

### Same model, concurrent requests (throughput)

On a **large** machine you may keep **several different** models loaded (e.g. small CIO + large coder) and get real **parallelism** across **different** model names.

**Do not** expect two **heavy concurrent** chat/generate jobs against the **same** model name to run at **2×** speed — Ollama typically **multiplexes** work on one loaded copy; competing long generations **hurt latency and effective throughput** (often feels like serial contention). **Orchestration pattern:** **one queue per model** (serialize CIO and coder if they share one tag), or **separate model tags / separate `ollama serve` instances** on different ports if you truly need same-architecture parallelism.

## See also

- `docs/guides/ide_execution_phases.md`
- `core/ide_agent.py`, `core/execution_agent.py` (re-export)
