# intent_flow.py

> 26 nodes · cohesion 0.11

## Key Concepts

- **intent_flow.py** (12 connections) — `app/graph/intent_flow.py`
- **local_intent_classifier.py** (11 connections) — `app/tools/local_intent_classifier.py`
- **classify_intent()** (8 connections) — `app/tools/local_intent_classifier.py`
- **run_prompt_agent.py** (5 connections) — `app/agents/run_prompt_agent.py`
- **run_prompt()** (5 connections) — `app/agents/run_prompt_agent.py`
- **classify_node()** (4 connections) — `app/graph/intent_flow.py`
- **handle_query()** (4 connections) — `app/graph/intent_flow.py`
- **handle_query_async()** (4 connections) — `app/graph/intent_flow.py`
- **IntentState** (4 connections) — `app/graph/intent_flow.py`
- **run_prompt_node()** (4 connections) — `app/graph/intent_flow.py`
- **intent_classifier.py** (4 connections) — `app/tools/intent_classifier.py`
- **classify_intent()** (4 connections) — `app/tools/intent_classifier.py`
- **_classify_with_llm()** (3 connections) — `app/tools/local_intent_classifier.py`
- **Any** (2 connections)
- **_load_model()** (2 connections) — `app/tools/local_intent_classifier.py`
- **langgraph_graph** (2 connections)
- **Any** (1 connections)
- **Load the prompt definition and return a mock response that satisfies its…** (1 connections) — `app/agents/run_prompt_agent.py`
- **TypedDict** (1 connections)
- **Classify the incoming query using the local LLM (or fallback).** (1 connections) — `app/graph/intent_flow.py`
- **Execute the matched prompt via the generic runner and store the result.** (1 connections) — `app/graph/intent_flow.py`
- **Run the intent‑classification & routing flow for *query*. Returns the final…** (1 connections) — `app/graph/intent_flow.py`
- **Synchronous wrapper for ``handle_query_async`` used by the API layer.** (1 connections) — `app/graph/intent_flow.py`
- **Return the best‑match prompt ID for *query*. Simple heuristic: first keyword…** (1 connections) — `app/tools/intent_classifier.py`
- **Return the prompt ID for *query*. Primary path: use the local quantised LLM. If…** (1 connections) — `app/tools/local_intent_classifier.py`
- *... and 1 more nodes in this community*

## Relationships

- [typing](typing.md) (4 shared connections)
- [SSEQueue](SSEQueue.md) (2 shared connections)
- [obs/store.py](obs-store.py.md) (2 shared connections)
- [chat_stream.py](chat_stream.py.md) (2 shared connections)
- [asyncio](asyncio.md) (1 shared connections)
- [re](re.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)
- [state.py](state.py.md) (1 shared connections)

## Source Files

- `app/agents/run_prompt_agent.py`
- `app/graph/intent_flow.py`
- `app/tools/intent_classifier.py`
- `app/tools/local_intent_classifier.py`

## Audit Trail

- EXTRACTED: 51 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*