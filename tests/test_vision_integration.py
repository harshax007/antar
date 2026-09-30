import pytest
import numpy as np
from app.second_brain.embedder import embed_query, embed_multimodal, embed, _model, load_embedder
from app.second_brain.index import BrainIndex
import anyio

def test_embed_query_dimension():
    load_embedder()
    # Phase 4 ensures embed_query returns 768 dimensions
    vec = embed_query("test query")
    assert vec.shape == (768,)
    # It should be L2 normalized
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-5)
    
def test_embed_multimodal_no_image():
    load_embedder()
    async def run_test():
        # If no image is provided, vision half should be zeros
        vec = await embed_multimodal("test document")
        assert vec.shape == (768,)
        
        # Text half is non-zero
        text_half = vec[:384]
        assert np.linalg.norm(text_half) > 0
        
        # Vision half is zero
        vision_half = vec[384:]
        assert np.linalg.norm(vision_half) == 0.0
        
        # Vector is normalized
        assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-5)
        
    anyio.run(run_test)
    


def test_legacy_rebuild_padding():
    # Simulate rebuilding an index from legacy 384-dim vectors
    import base64
    
    idx = BrainIndex()
    # Create a dummy 384-dim vector
    dummy_vec = np.ones(384, dtype=np.float32)
    dummy_vec = dummy_vec / np.linalg.norm(dummy_vec)
    b64_vec = base64.b64encode(dummy_vec.tobytes()).decode('ascii')
    
    rows = [{
        "row_id": "legacy_1",
        "vector_b64": b64_vec,
        "summary_text": "legacy text"
    }]
    
    idx.rebuild(rows)
    assert idx.size == 1
    assert idx._matrix.shape == (1, 768)
    
    # Vision half should be exactly zeros
    assert np.all(idx._matrix[0, 384:] == 0.0)
