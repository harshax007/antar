"""
Antar — Zero-Parameter Self-Attention Rerank
Computes document centrality (corroboration) by applying self-attention over the cosine similarity matrix.
"""

import numpy as np

def compute_attention_scores(embeddings: np.ndarray, temperature: float = 0.1) -> np.ndarray:
    """
    Computes a centrality score for each document in the batch based on its 
    attention (similarity) to all other documents in the batch.
    
    Args:
        embeddings: (N, D) float32 numpy array of L2-normalized embeddings.
        temperature: Scaling factor for the softmax to sharpen the distribution.
        
    Returns:
        (N,) float32 numpy array of centrality scores in [0, 1].
    """
    if len(embeddings) == 0:
        return np.array([])
        
    if len(embeddings) == 1:
        return np.array([1.0])
        
    # Since embeddings are L2 normalized, Q @ K^T is the cosine similarity matrix
    # shape: (N, N)
    sim_matrix = embeddings @ embeddings.T
    
    # Scale by temperature (equivalent to division by sqrt(d_k) in standard attention, but tunable)
    scaled_sim = sim_matrix / temperature
    
    # Stabilize softmax
    max_sim = np.max(scaled_sim, axis=1, keepdims=True)
    exp_sim = np.exp(scaled_sim - max_sim)
    
    # Softmax over rows (how much each document attends to others)
    attention_weights = exp_sim / np.sum(exp_sim, axis=1, keepdims=True)
    
    # Centrality (how much *other* documents attend to this document)
    # Sum the columns of the attention matrix
    centrality = np.sum(attention_weights, axis=0)
    
    # Normalize to [0, 1] relative to the most central document
    max_c = np.max(centrality)
    if max_c > 0:
        centrality = centrality / max_c
        
    return centrality.astype(np.float32)
