"""
Answer guardrails — post-generation enforcement of the chat answer contract.

Each test feeds a DELIBERATELY VIOLATING answer (the kind a model actually produces
under pressure) and asserts the guardrail neutralises it. Prompt rules are advisory;
these are the enforcement.

  G1 numbers      — an invented figure is dropped
  G2 no-result    — empty rows must lead with the absence, never related material
  G3 identifiers  — an invented FIR/ACC id is dropped
  G4 slop         — filler phrases removed
  G6 length       — per-type sentence budget
  + never raises, never returns empty, never invents a replacement
"""

import pytest

from app.core.answer_guardrails import (
    apply_guardrails, cap_length, check_identifiers, check_numbers,
    enforce_no_result, strip_slop,
)

ROWS = [
    {"crime_id": "C02781", "fir_number": "2026-BLR-P2-2780", "zone": "Rajajinagar",
     "crime_type": "chain_snatching", "occurred_at": "2026-05-14", "status": "Under Investigation"},
    {"crime_id": "C02782", "fir_number": "2026-BLR-P2-2781", "zone": "Rajajinagar",
     "crime_type": "chain_snatching", "occurred_at": "2026-05-19", "status": "Closed"},
]


class TestG1Numbers:
    def test_drops_sentence_with_invented_number(self):
        ans = "There are 2 chain snatching cases in Rajajinagar. Arrests rose by 47 percent last quarter."
        out, dropped = check_numbers(ans, ROWS)
        assert dropped, "invented 47 should have been flagged"
        assert "47 percent" not in out
        assert "2 chain snatching" in out

    def test_keeps_supported_numbers(self):
        ans = "There are 2 chain snatching cases in Rajajinagar."
        out, dropped = check_numbers(ans, ROWS)
        assert not dropped and out == ans

    def test_row_count_is_always_allowed(self):
        ans = "Found 2 records."
        out, dropped = check_numbers(ans, ROWS)
        assert not dropped and "2" in out

    def test_no_rows_is_a_noop(self):
        ans = "Nothing here 999."
        out, dropped = check_numbers(ans, [])
        assert out == ans and not dropped


class TestG2NoResult:
    def test_related_material_cannot_masquerade_as_answer(self):
        """The exact failure mode the owner asked to eliminate."""
        ans = "Rajajinagar has seen significant chain snatching activity this year."
        out, forced = enforce_no_result(ans, [], "burglaries in Whitefield", "en")
        assert forced
        assert out.lower().startswith("no records found")
        assert "burglaries in Whitefield" in out

    def test_accepts_an_already_honest_answer(self):
        ans = "No burglary records found for Whitefield in that period."
        out, forced = enforce_no_result(ans, [], "burglaries in Whitefield", "en")
        assert not forced and out == ans

    def test_kannada_negative_is_recognised(self):
        ans = "ಈ ಪ್ರಶ್ನೆಗೆ ಹೊಂದುವ ದಾಖಲೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ."
        out, forced = enforce_no_result(ans, [], "ಪ್ರಶ್ನೆ", "kn")
        assert not forced and out == ans

    def test_kannada_fallback_is_in_kannada(self):
        out, forced = enforce_no_result("Some unrelated prose.", [], "ಪ್ರಶ್ನೆ", "kn")
        assert forced and "ಕಂಡುಬಂದಿಲ್ಲ" in out

    def test_with_rows_is_a_noop(self):
        ans = "Two cases found."
        out, forced = enforce_no_result(ans, ROWS, "q", "en")
        assert not forced and out == ans


class TestG3Identifiers:
    def test_drops_invented_fir_number(self):
        ans = "Case 2026-BLR-P2-2780 is under investigation. See also 2026-MYS-Q9-9999 for context."
        out, dropped = check_identifiers(ans, ROWS)
        assert dropped
        assert "2026-MYS-Q9-9999" not in out
        assert "2026-BLR-P2-2780" in out

    def test_keeps_real_identifiers(self):
        ans = "Case 2026-BLR-P2-2781 is closed."
        out, dropped = check_identifiers(ans, ROWS)
        assert not dropped and out == ans


class TestG4Slop:
    def test_removes_filler_phrases(self):
        ans = "It is worth noting that 2 cases exist. In conclusion, the trend is flat."
        out, n = strip_slop(ans)
        assert n >= 2
        low = out.lower()
        assert "it is worth noting" not in low and "in conclusion" not in low
        assert "2 cases exist" in out

    def test_clean_text_untouched(self):
        ans = "Two chain snatching cases in Rajajinagar."
        out, n = strip_slop(ans)
        assert n == 0 and out == ans


class TestG6Length:
    def test_caps_count_answers_to_budget(self):
        ans = "A one. B two. C three. D four. E five."
        out, capped = cap_length(ans, "COUNT")
        assert capped and out.count(".") == 2

    def test_never_truncates_tables(self):
        ans = "Header line.\n\n| FIR | Date |\n|---|---|\n| a | b |\n| c | d |\n| e | f |"
        out, capped = cap_length(ans, "COUNT")
        assert not capped and out == ans


class TestApplyGuardrails:
    def test_end_to_end_cleans_a_hostile_answer(self):
        ans = ("It is worth noting that there are 2 chain snatching cases in Rajajinagar. "
               "Arrests increased 47 percent. Case 2026-MYS-Q9-9999 is related.")
        res = apply_guardrails(ans, ROWS, "chain snatching in Rajajinagar", "en", "T1")
        assert res["changed"]
        assert "it is worth noting" not in res["answer"].lower()
        assert "47 percent" not in res["answer"]
        assert "2026-MYS-Q9-9999" not in res["answer"]
        assert res["violations"]

    def test_clean_answer_passes_untouched(self):
        ans = "There are 2 chain snatching cases in Rajajinagar."
        res = apply_guardrails(ans, ROWS, "q", "en", "T1")
        assert not res["changed"] and res["answer"] == ans and not res["violations"]

    def test_never_returns_empty(self):
        res = apply_guardrails("999999 fabricated 888888.", ROWS, "q", "en", "T1")
        assert res["answer"].strip()
        # ... but an answer with nothing supportable in it is marked, so the caller
        # writes one from the rows rather than showing the invention
        assert res["rejected"] is True and "unsupported_answer_rejected" in res["violations"]

    def test_a_partly_supported_answer_is_trimmed_not_rejected(self):
        res = apply_guardrails("There are 2 chain snatching cases in Rajajinagar. Arrests rose by 47 percent.",
                               ROWS, "q", "en", "T1")
        assert "rejected" not in res and "47 percent" not in res["answer"]

    def test_never_raises_on_garbage_input(self):
        for bad in (None, "", "   "):
            res = apply_guardrails(bad, None, "q", "en", "")
            assert "answer" in res and "violations" in res
        res = apply_guardrails("text", [{"weird": object()}], "q", "en", "T1")
        assert "answer" in res
