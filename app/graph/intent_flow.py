import asyncio
from typing import Any, Dict

# Import the local intent classifier (implemented in Phase 2)
from app.tools.local_intent_classifier import classify_intent
# Generic prompt runner that returns a mock or real response
from app.agents.run_prompt_agent import run_prompt

from typing import TypedDict

class IntentState(TypedDict, total=False):
    query: str
    prompt_id: str
    result: dict

# LangGraph Nodes
async def classify_node(state: IntentState) -> IntentState:
    """Classify the incoming query using the local LLM (or fallback)."""
    query = state.get("query", "")
    # Returns the prompt ID (e.g., "int_01" or "default")
    prompt_id = classify_intent(query)
    return {"prompt_id": prompt_id}

async def run_prompt_node(state: IntentState) -> IntentState:
    """Execute the matched prompt via the generic runner and store the result."""
    prompt_id = state.get("prompt_id", "default")
    query = state.get("query", "")
    # The runner returns a dict obeying the prompt's output_schema
    result = run_prompt(prompt_id, query)
    return {"result": result}

# Build the LangGraph – two sequential steps then finish
from langgraph.graph import StateGraph

graph = StateGraph(IntentState)
graph.add_node("classify", classify_node)
graph.add_node("run_prompt", run_prompt_node)
graph.add_edge("classify", "run_prompt")
graph.set_entry_point("classify")
graph.set_finish_point("run_prompt")

# Compile the async graph so it can be invoked from the API layer
app_graph = graph.compile()

# Public helper functions used by the FastAPI endpoint (or any caller)
async def handle_query_async(query: str) -> Dict[str, Any]:
    """Run the intent‑classification & routing flow for *query*.
    Returns the final state containing ``prompt_id`` and ``result``.
    """
    return await app_graph.ainvoke({"query": query})

def handle_query(query: str) -> Dict[str, Any]:
    """Synchronous wrapper for ``handle_query_async`` used by the API layer."""
    return asyncio.run(handle_query_async(query))
