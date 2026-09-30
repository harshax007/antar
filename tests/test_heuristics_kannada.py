"""Kannada intent-routing regressions (Phase 1 fix).

`ಕಲ್ಲತನ ಯಾವ ಊರಿನಲ್ಲಿ ಜಾಸ್ತಿ ಇದೆ` ("which town has the most theft") used to fall
through to NONE → an English "please rephrase" answer. It must route to the
hotspot template with the crime type resolved and a Kannada answer language.
"""

import asyncio

from app.agents.heuristics import heuristic_select, is_kannada


def test_kannada_theft_hotspot_routes_to_t11():
    out = asyncio.run(heuristic_select("ಕಲ್ಲತನ ಯಾವ ಊರಿನಲ್ಲಿ ಜಾಸ್ತಿ ಇದೆ", lang=None))
    assert out["template_id"] == "T11"
    assert out["params"]["crime_types"] == ["THEFT"]
    assert out["answer_lang"] == "kn"


def test_kannada_canonical_spelling_still_routes():
    assert is_kannada("ಕಳ್ಳತನ ಎಲ್ಲಿ ಜಾಸ್ತಿ ಇದೆ")
    out = asyncio.run(heuristic_select("ಕಳ್ಳತನ ಎಲ್ಲಿ ಜಾಸ್ತಿ ಇದೆ", lang=None))
    assert out["template_id"] == "T11"
    assert out["params"]["crime_types"] == ["THEFT"]
    assert out["answer_lang"] == "kn"
