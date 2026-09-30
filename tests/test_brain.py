"""
Second Brain — demo seeding (fake embedder) + /api/brain/related (WOW2, data-driven).
Run: python -m pytest tests/test_brain.py -v
"""

import asyncio

import numpy as np

from app.second_brain.index import brain_index
from app.second_brain.ingestion import seed_demo_brain, session_end_ingest
from app.second_brain.consolidation import consolidate_nightly
from app.api.brain import related
from app.seeds.planted_patterns import BRAIN_SEED
from app.core import sessions


def _fake_embed(text):
    """Deterministic normalized 384-d vector — avoids loading MiniLM in unit tests."""
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    v = rng.standard_normal(384).astype(np.float32)
    return (v / np.linalg.norm(v)).reshape(1, 384)


def test_seed_demo_brain_is_idempotent():
    brain_index.rebuild([])                       # reset to empty
    try:
        n1 = seed_demo_brain(_fake_embed)
        assert n1 == len(BRAIN_SEED)
        assert brain_index.size == len(BRAIN_SEED)
        assert seed_demo_brain(_fake_embed) == 0   # idempotent — no duplicates
        assert brain_index.size == len(BRAIN_SEED)
    finally:
        brain_index.rebuild([])                   # leave the global index clean for other tests


def test_brain_related_surfaces_wow2_link():
    """WOW2 is data-driven (shared phone + common contacts) — no embedder required."""
    out = asyncio.run(related("S0001"))
    assert out["results"][0]["links"]             # cross-case link present
    assert out["banner"] and "yellappa" in out["banner"].lower()  # link is described

def test_session_ingestion_and_consolidation():
    brain_index.rebuild([])  # clear index
    
    # 1. Create a mock session
    sid1 = "test-session-1"
    sessions.clear(sid1)
    sessions.append_user_turn(sid1, "What did the suspect wear?", "en")
    sessions.append_assistant_turn(sid1, "A red jacket.", "en", "T1", "rsn1", [{"detail": "Found red jacket description"}])
    
    # 2. Ingest
    # We must patch the embedder to use fake_embed inside session_end_ingest since it imports the real one
    import app.second_brain.ingestion
    real_embed = app.second_brain.ingestion._embed_one
    app.second_brain.ingestion._embed_one = lambda fn, text, terms=None: _fake_embed(text)
    
    try:
        success = asyncio.run(session_end_ingest(sid1, "Inspector"))
        assert success
        assert brain_index.size == 1
        meta = brain_index._metadata[0]
        assert meta["verification_status"] == "unverified"
        assert meta["confidence"] == 0.6
        
        # 3. Create another mock session that should cluster
        sid2 = "test-session-2"
        sessions.clear(sid2)
        sessions.append_user_turn(sid2, "Details on the red jacket suspect?", "en")
        sessions.append_assistant_turn(sid2, "He was seen downtown.", "en", "T1", "rsn2", [{"detail": "Suspect in red jacket downtown"}])
        asyncio.run(session_end_ingest(sid2, "Constable"))
        
        assert brain_index.size == 2
        
        # Manually force the second embedding to be exactly the same as the first so it guarantees a cluster > 0.85
        brain_index._matrix[1] = brain_index._matrix[0]
        
        # 4. Consolidate
        res = asyncio.run(consolidate_nightly())
        assert res["status"] == "success"
        # The first should now be 'verified' because it overlapped with the second
        assert brain_index._metadata[0]["verification_status"] == "verified"
        assert brain_index._metadata[0]["confidence"] == 0.9
        assert "Found red jacket" in brain_index._metadata[0]["summary_text"]
    finally:
        app.second_brain.ingestion._embed_one = real_embed
        brain_index.rebuild([])

