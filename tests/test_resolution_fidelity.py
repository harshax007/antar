"""
Resolution fidelity — did every filter the officer NAMED actually reach the query?

The bug this exists to catch is the one that looks most like success. A dropped filter
always returns MORE rows, never fewer, and more rows read as a confident answer: "how many
riots cases in Karnataka?" came back as **995,452 FIRs** — the size of the whole registry —
tagged `[VERIFIED]` at 0.99 confidence, because `RIOTS` never reached `crime_types` and so
there was nothing for `unresolved_filters()` to refuse.

Two separate guarantees are tested here:

* the detector notices a named filter that did not run, and stays quiet otherwise;
* the confidence score actually MOVES when it does, because a score that reads 0.99 for
  both a right and a wrong answer cannot warn anyone about anything.
"""

from __future__ import annotations

from app.agents.query_agent import _named_crime_phrase, resolution_fidelity
from app.api.chat_stream import _answer_confidence


# ── the detector ─────────────────────────────────────────────────────────────

def test_a_named_crime_that_never_reached_the_query_is_caught():
    fid, gaps = resolution_fidelity("How many riots cases in Karnataka?", {"crime_types": []})
    assert fid < 0.6, "a dropped crime filter must cost most of the confidence"
    assert gaps and "riots" in gaps[0]
    assert "every crime type" in gaps[0], "the officer is told what the answer actually counts"


def test_nothing_is_flagged_when_the_filter_did_run():
    fid, gaps = resolution_fidelity("How many riots cases in Karnataka?",
                                    {"crime_types": ["RIOTS"]})
    assert (fid, gaps) == (1.0, [])


def test_a_dropped_year_is_caught():
    fid, gaps = resolution_fidelity("How many theft cases in Kodagu in 2018?",
                                    {"crime_types": ["THEFT"]})
    assert fid < 1.0
    assert "2018" in gaps[0] and "every year" in gaps[0]


def test_an_applied_year_is_not_flagged():
    for applied in ({"date_from": "2018-01-01"}, {"period": "this_year"}, {"year": 2018}):
        fid, gaps = resolution_fidelity("How many theft cases in Kodagu in 2018?",
                                        {"crime_types": ["THEFT"], **applied})
        assert (fid, gaps) == (1.0, []), applied


def test_an_unknown_place_is_caught():
    fid, gaps = resolution_fidelity("How many theft cases in Atlantis?",
                                    {"crime_types": ["THEFT"], "unknown_place": "Atlantis"})
    assert fid < 1.0 and "Atlantis" in gaps[0]


def test_several_gaps_compound():
    """Two things missing must cost more than one. Otherwise the score plateaus again."""
    one, _ = resolution_fidelity("How many riots cases in Karnataka?", {"crime_types": []})
    two, gaps = resolution_fidelity("How many riots cases in Karnataka in 2018?",
                                    {"crime_types": []})
    assert two < one and len(gaps) == 2


# ── what must NOT be flagged ─────────────────────────────────────────────────
# A heuristic over free text earns its place only if it is quiet on good questions.
# Refusing or discounting an answerable question is a worse failure than widening one.

def test_a_plain_fir_count_is_not_a_missing_crime_filter():
    assert _named_crime_phrase("How many FIRs are on record in Bidar?") is None
    assert resolution_fidelity("How many FIRs are on record in Bidar?", {}) == (1.0, [])


def test_a_non_crime_qualifier_is_not_mistaken_for_a_crime_type():
    """"cognizable" is a FIR type, not a crime group — and that question is answerable."""
    for q in ("How many cognizable cases in Mysuru?",
              "How many open cases in Jayanagar?",
              "How many pending cases are on record?"):
        assert _named_crime_phrase(q) is None, q
        assert resolution_fidelity(q, {})[1] == [], q


def test_a_bare_number_is_not_read_as_a_year():
    fid, gaps = resolution_fidelity("Top 10 districts by theft", {"crime_types": ["THEFT"]})
    assert (fid, gaps) == (1.0, [])


def test_no_params_and_no_named_filters_is_clean():
    assert resolution_fidelity("hello", {}) == (1.0, [])
    assert resolution_fidelity("", None) == (1.0, [])


# ── the score has to move ────────────────────────────────────────────────────

def test_confidence_falls_when_a_filter_was_dropped():
    clean = _answer_confidence(0.95, [1, 2, 3], [1, 2, 3])
    lost = _answer_confidence(0.95, [1, 2, 3], [1, 2, 3], "en", 0.5,
                              ['crime type "riots" was not applied'])
    assert clean["answer"] > 0.9
    assert lost["answer"] < 0.6, "the whole point: the score must discriminate"
    assert lost["answer"] < clean["answer"] / 1.5


def test_the_label_says_which_part_did_not_run():
    lost = _answer_confidence(0.95, [1, 2, 3], [1, 2, 3], "en", 0.5,
                              ['crime type "riots" was not applied'])
    assert "Broader than asked" in lost["label"]
    assert "riots" in lost["label"]
    assert lost["gaps"] == ['crime type "riots" was not applied']


def test_a_clean_answer_carries_no_gap_fields():
    """No gaps means no noise: the payload must not grow a fidelity block for nothing."""
    clean = _answer_confidence(0.95, [1, 2, 3], [1, 2, 3])
    assert "gaps" not in clean and "fidelity" not in clean


def test_fidelity_is_clamped():
    assert _answer_confidence(0.9, [1], [1], "en", 5.0)["answer"] <= 1.0
    assert _answer_confidence(0.9, [1], [1], "en", -3.0)["answer"] == 0.0


def test_kannada_label_is_translated():
    lost = _answer_confidence(0.95, [1, 2, 3], [1, 2, 3], "kn", 0.5, ["year 2018 was not applied"])
    assert "ಕೇಳಿದ್ದಕ್ಕಿಂತ ವಿಶಾಲ" in lost["label"]


# ── partial matches: the subtler half of the same bug ────────────────────────
# A term that matches only PART of what the officer said still runs a filter, so the
# earlier checks all pass and the score stays high — while the answer is about a
# different, broader offence. Found by running the detector end to end rather than by
# reasoning about it.

def test_a_partially_matched_crime_is_flagged():
    fid, gaps = resolution_fidelity("How many dacoity-by-drone cases in Mysuru?",
                                    {"crime_types": ["DACOITY"]})
    assert fid < 1.0, "a filter ran, but not the one that was asked for"
    assert "only part of" in gaps[0]
    assert "drone" in gaps[0], "the officer is told exactly which word was ignored"


def test_an_exact_match_is_not_called_partial():
    assert resolution_fidelity("How many theft cases in Mysuru?",
                               {"crime_types": ["THEFT"]}) == (1.0, [])


def test_connectors_inside_a_real_phrase_are_not_residue():
    """"crimes related to women" is a real group — "related"/"to" must not look unmatched."""
    assert resolution_fidelity("How many crimes related to women cases in Bagalkot?",
                               {"crime_types": ["CRIMES RELATED TO WOMEN"]}) == (1.0, [])


def test_question_scaffolding_is_never_reported_as_a_crime_type():
    """"How many cases in Atlantis?" once reported a missing crime type called "how many"."""
    assert _named_crime_phrase("How many cases in Atlantis?") is None
    _fid, gaps = resolution_fidelity("How many cases in Atlantis?",
                                     {"unknown_place": "Atlantis"})
    assert all("how many" not in g for g in gaps)
    assert gaps and "Atlantis" in gaps[0]
