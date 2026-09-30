"""
Tests for Phase 6 OSINT service.
"""
import pytest
from app.services.osint import search_osint

@pytest.mark.anyio
async def test_search_osint():
    # Test with a made up name that will either hit the scraper or the fallback.
    # In both cases, we expect a deterministic structure.
    res = await search_osint("John Doe")
    
    assert "claims" in res
    assert "risk_flags" in res
    assert "summary" in res
    
    # We should have at least 1 claim (either from DDG or fallback)
    assert len(res["claims"]) > 0
    
    claim = res["claims"][0]
    assert "claim" in claim
    assert "source_url" in claim
    assert claim["status"] == "unverified"
    assert claim["confidence"] <= 0.6
