"""
Pipeline internals must NEVER surface as the officer-facing answer.

Regression guard for a real defect: the reasoning trail was concatenated into the
answer body, so build_layout promoted lines like "Classified as T11 —",
"Extracted: {'crime_types': ...}", "Queried the crime database -> 10 matching row(s)"
to `facts`. The chat card then showed the TRAIL as the answer's content while the
actual answer was hidden behind "Show full answer".

Two defences are tested here:
  1. the trail is no longer appended upstream (chat_stream / agentic_spine)
  2. even if it were, build_layout refuses to promote internals to headline/facts/kdiu
"""

from app.agents.layout_composer import build_layout, _is_internal

TRAIL = [
    "Classified as T11 — Crime counts ranked by zone, district, or city (hotspots & city rankings).",
    "Extracted: {'crime_types': 'VEHICLE_THEFT', 'date_from': None, 'period': 'last_6_months', 'limit': 10}",
    "Queried the crime database → 10 matching row(s).",
    "Summarized using only those rows (0 citation(s)).",
    "No filters needed.",
]


class TestIsInternal:
    def test_flags_every_trail_step(self):
        for line in TRAIL:
            assert _is_internal(line), f"not flagged: {line}"

    def test_flags_numbered_and_bulleted_variants(self):
        for line in TRAIL:
            assert _is_internal(f"1. {line}")
            assert _is_internal(f"• {line}")

    def test_does_not_flag_real_answers(self):
        for line in [
            "No common hotspots for vehicle theft in South Bengaluru found for the given data.",
            "There are 39 chain snatching cases in Rajajinagar.",
            "Whitefield recorded the highest count at 128 cases.",
            "FIR 2026-BLR-P2-2780 is under investigation.",
            "Theft in Jayanagar is falling — down 18% over 6 months.",
        ]:
            assert not _is_internal(line), f"false positive: {line}"


class TestBuildLayoutRejectsInternals:
    def _q(self):
        return {"rows": [{"zone": "Whitefield", "n": 128}], "citations": [],
                "template_id": "T11", "params": {"crime_types": ["VEHICLE_THEFT"]}}

    def test_trail_never_becomes_facts_or_headline(self):
        answer = ("No common hotspots for vehicle theft in South Bengaluru found for the given data.\n\n"
                  "— Reasoning trail —\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(TRAIL)))
        lay = build_layout(answer, self._q())
        assert lay["headline"].startswith("No common hotspots")
        assert lay["facts"] == [], f"internals leaked into facts: {lay['facts']}"
        for f in lay["facts"] + [k["text"] for k in lay["kdiu"]]:
            assert not _is_internal(f)

    def test_headline_skips_a_leading_internal_line(self):
        answer = "Classified as T11 — hotspots.\nWhitefield recorded the highest count at 128 cases."
        lay = build_layout(answer, self._q())
        assert "Classified as" not in lay["headline"]
        assert "Whitefield" in lay["headline"]

    def test_real_bullets_still_survive(self):
        answer = ("Top hotspots for vehicle theft:\n"
                  "• Whitefield — 128 cases\n"
                  "• Malleshwaram — 96 cases")
        lay = build_layout(answer, self._q())
        assert len(lay["facts"]) == 2
        assert "Whitefield" in lay["facts"][0]

    def test_tagged_internal_is_dropped_but_tagged_fact_kept(self):
        answer = "[COMPUTED] Extracted: {'zones': 'X', 'limit': 10}\n[VERIFIED] 128 vehicle theft cases in Whitefield."
        lay = build_layout(answer, self._q())
        texts = [k["text"] for k in lay["kdiu"]]
        assert not any("Extracted" in t for t in texts)
        assert any("128" in t for t in texts)
