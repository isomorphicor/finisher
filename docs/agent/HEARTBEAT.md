## Heartbeat (Operating Loop)

`HEARTBEAT.md` defines the agent’s default operating loop: how we go from intent to evidence to executable results.

### Default loop (every cycle)

1. **Clarify**: Rewrite the goal as verifiable pass/fail criteria and list key assumptions.
2. **Plan**: Provide the minimum viable evidence path and a concrete experiment/implementation breakdown.
3. **Act**: Produce structured artifacts first (plans/checklists/skeletons), then run experiments/execute.
4. **Verify**: Check structure, protocol, and evidence; for quant work, validate against **locked** acceptance rules when they exist (scheme phase may keep targets `provisional` per `quant_soul`); missing evidence = fail.
5. **Record**: Persist only long-lived decisions in `MEMORY.md` (everything else stays in session artifacts).

### Quality bar

- **Structure before detail**: Make the artifact outline complete before filling in details.
- **Baselines before frontier**: Anchor with robust baselines before high-variance candidates.
- **Budgeted cost**: Declare time/compute budget and explicit stop rules before expensive runs.

