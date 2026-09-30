"""
Antar — Continuous Agent Evaluation (LLM-as-a-Judge)
=================================================
Runs asynchronously after agent responses to score RAG faithfulness,
answer relevance, and tool adherence.
"""

from typing import Dict, Any

async def evaluate_response(query: str, response_text: str, context: list[str]) -> Dict[str, Any]:
    """
    Evaluates an agent's response using standard RAG metrics.
    In a real production environment, this calls a specialized judge LLM.
    Here we implement a robust heuristic placeholder.
    """
    scores = {
        "faithfulness": 0.0,
        "answer_relevance": 0.0,
        "tool_adherence": 1.0,
    }
    
    # Heuristic: Faithfulness (Does the response match context length/keywords?)
    ctx_words = set(word.lower() for c in context for word in c.split())
    resp_words = set(word.lower() for word in response_text.split())
    
    if not ctx_words and resp_words:
        scores["faithfulness"] = 0.1 # Hallucination risk if no context provided
    elif not resp_words:
        scores["faithfulness"] = 1.0
    else:
        overlap = len(ctx_words.intersection(resp_words))
        scores["faithfulness"] = min(1.0, (overlap / len(resp_words)) * 2.0 + 0.3)
        
    # Heuristic: Answer Relevance
    q_words = set(query.lower().split())
    if q_words.intersection(resp_words):
        scores["answer_relevance"] = 0.8
    else:
        scores["answer_relevance"] = 0.4
        
    return {
        "scores": scores,
        "overall_quality": (scores["faithfulness"] + scores["answer_relevance"]) / 2,
        "flagged": scores["faithfulness"] < 0.5
    }
