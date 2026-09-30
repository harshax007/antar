"""
Antar — Nightly Consolidation Engine ($100B Standard)
=========================================================
Runs nightly to cluster overlapping intelligence fragments, promote verified 
findings, and apply mathematical confidence decay to stale unverified data.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from app.second_brain.index import brain_index

router = APIRouter()

async def consolidate_nightly() -> dict:
    """
    Scans the in-memory brain_index for 'unverified' fragments.
    1. Verification Decay: Halves confidence for unverified fragments > 30 days old.
    2. Probabilistic Merging: Finds overlapping fragments from different sessions
       (cosine > 0.85) and merges them into a 'verified' insight.
    """
    now = datetime.utcnow()
    decayed_count = 0
    merged_count = 0
    
    unverified_indices = []
    
    # 1. Verification Decay
    for i, meta in enumerate(brain_index._metadata):
        if meta.get("verification_status") == "unverified":
            created_at_str = meta.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_days = (now - created_at).days
                    if age_days > 30:
                        # Apply Decay
                        meta["confidence"] = max(0.1, meta.get("confidence", 0.6) * 0.5)
                        meta["verification_status"] = "decayed"
                        decayed_count += 1
                        continue
                except ValueError:
                    pass
            unverified_indices.append(i)
            
    # 2. Probabilistic Merging (simplified heuristic for fallback)
    # In a full run, QuickML merges the texts.
    processed = set()
    
    from app.second_brain.ingestion import _embed_one
    from app.second_brain.embedder import embed
    
    for i in unverified_indices:
        if i in processed:
            continue
            
        vec_i = brain_index._matrix[i]
        meta_i = brain_index._metadata[i]
        
        # Find similar
        results = brain_index.cosine_topk(vec_i, k=5, kind_filter="session_trace")
        overlaps = [res for res in results if res["score"] > 0.85 and res["row_id"] != brain_index._row_ids[i]]
        
        if overlaps:
            # We found corroboration!
            
            # -- Phase 3: Self-Attention Rerank --
            # 1. Collect all vectors in the cluster (including self)
            cluster_indices = [i]
            for o in overlaps:
                try:
                    cluster_indices.append(brain_index._row_ids.index(o["row_id"]))
                except ValueError:
                    continue
            
            import numpy as np
            from app.second_brain.attention_rerank import compute_attention_scores
            
            cluster_vecs = brain_index._matrix[cluster_indices]
            scores = compute_attention_scores(cluster_vecs)
            
            # Store attention scores in metadata
            for idx_in_cluster, global_idx in enumerate(cluster_indices):
                brain_index._metadata[global_idx]["attention_score"] = float(scores[idx_in_cluster])
            
            # Determine the primary fragment (highest centrality)
            primary_idx_in_cluster = int(np.argmax(scores))
            primary_global_idx = cluster_indices[primary_idx_in_cluster]
            primary_meta = brain_index._metadata[primary_global_idx]
            
            # Upgrade the primary fragment to verified
            primary_meta["verification_status"] = "verified"
            primary_meta["confidence"] = 0.9
            
            # Combine text into the primary fragment
            combined_text = primary_meta["summary_text"]
            for idx_in_cluster, global_idx in enumerate(cluster_indices):
                if global_idx == primary_global_idx:
                    continue
                other_meta = brain_index._metadata[global_idx]
                combined_text += f" | {other_meta['summary_text']}"
                # Mark overlapped as processed so we don't double merge
                processed.add(global_idx)
                
            primary_meta["summary_text"] = combined_text[:1500]  # Cap length
            
            # Re-embed the merged text with entity terms if available
            import json as _json
            terms = []
            try:
                terms.extend(_json.loads(primary_meta.get("suspect_ids_json", "[]")))
            except Exception:
                pass
            if primary_meta.get("station_code"):
                terms.append(primary_meta["station_code"])
            
            # Phase 4: Average the visual halves of the cluster vectors
            vision_parts = cluster_vecs[:, 384:]
            avg_vision = np.mean(vision_parts, axis=0)
            
            # Re-embed text to 384
            text_vec = _embed_one(embed, primary_meta["summary_text"], terms or None)
            
            # Combine to 768 and normalize
            combined = np.concatenate([text_vec.flatten(), avg_vision])
            norm = np.linalg.norm(combined)
            if norm > 0:
                combined = combined / norm
                
            brain_index._matrix[primary_global_idx] = combined.reshape(1, -1)
            # FAISS HNSW cannot update vectors in-place; resync from _matrix
            brain_index.sync_faiss()
            
            merged_count += 1
            processed.add(i)

    return {
        "status": "success",
        "decayed": decayed_count,
        "merged": merged_count,
        "total_unverified_scanned": len(unverified_indices)
    }
