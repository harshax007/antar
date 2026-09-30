# Antar Observability Fix Playbook

When the Trust Dashboard flags traces or the LLM Judge identifies issues, use this playbook to map the `failure_point` tag to the correct component to fix.

## Failure Point Mapping

### 1. `retriever` (Rules F1, F2, F5)
**Symptom**: The model answered with data not found in the rows, or was confident despite no matching records.
**Fix Location**: 
- **Template Selection**: Check `app/agents/query_agent.py` in `select_template()`.
- **ZCqL Execution**: Verify `run_template()` logic.
- **SQL Templates**: Inspect the exact template in `app/services/zcql_repo.py`.

### 2. `prompt` (Rule F7 - Groundedness/Format)
**Symptom**: The model ignored formatting rules (e.g. used bullet points for single facts) or added filler text.
**Fix Location**:
- Update `COMPOSE_SYSTEM` or `COMPOSE_USER_TMPL` inside `app/agents/query_agent.py`.

### 3. `chunking` (Rule F3 token spikes / Missing Context)
**Symptom**: The model missed context because rows were truncated, or latency spiked due to oversized inputs.
**Fix Location**:
- Adjust row limiting in `_slim_rows_for_compose()` within `app/agents/query_agent.py`.
- Verify the keys being stripped in `_COMPOSE_DROP_KEYS`.

### 4. `model` (Rule F3 Latency/Token Blowups)
**Symptom**: Massive token usage spikes or extreme latencies beyond baseline.
**Fix Location**:
- Swap the model or reduce `temperature`/`max_tokens` in `app/core/settings.py`.
- Verify `QUICKML_DEFAULT_MODEL` and `QUICKML_CHAT_MODEL`.

### 5. `tool` (Agent Errors)
**Symptom**: Errors originating from specialized agents (e.g., Network, Forecast).
**Fix Location**:
- Inspect the respective tool in `app/agents/` (e.g. `network_agent.py`, `forecast_agent.py`).

## Continuous Evaluation (Promoting Fixes)
After applying a fix:
1. Bump `PROMPT_VERSION` in `app/core/settings.py`.
2. Run the eval suite: `python scripts/run_eval.py`.
3. Only promote to production if the `pass_rate` and `avg_grounded` scores improve or remain stable without increasing `p95_ms` latency. If they regress, it will trigger an **F4 (Version Regression)** flag.
