"""Chat answers read in the officer's language, and say what the register says.

Each test is a bug the answers had: ISO dates and English month and day names inside a
Kannada answer, "3 ತಿಂಗಳು ಗಿಂತ", a Kannada "Mysuru city" question counted over the whole of
Mysuru, a z-score and a "confidence 50%" in the alerts list, and a case's similar cases "0%
reached court" because the 2026 rows spell their stages CHARGE_SHEETED and DISPOSED.
"""
from app.agents import answer_writer as W
from app.agents import heuristics as H
from app.agents.display_names import display_crime
from app.services import case_timeline as CT


def test_dates_read_as_dates_in_both_languages():
    assert W._date("2016-04-17") == "2016-04-17"            # no language: still sortable
    assert W._date("2016-04-17", False) == "17 Apr 2016"
    assert W._date("2016-04-17", True) == "17 ಏಪ್ರಿಲ್ 2016"
    assert CT._nice("2026-07-14", True) == "14 ಜುಲೈ 2026"


def test_kannada_comparative_and_singular():
    assert W._more_than_kn(90) == "3 ತಿಂಗಳಿಗಿಂತ"
    assert W._more_than_kn(365) == "1 ವರ್ಷಕ್ಕಿಂತ"
    assert W._more_than_kn(45) == "45 ದಿನಗಳಿಗಿಂತ"
    assert W._slot("Wednesday", True) == "ಬುಧವಾರ" and W._slot("Wednesday", False) == "Wednesday"


def test_kannada_city_names_are_the_city_not_the_district():
    assert H._match_places(H._norm("ಮೈಸೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ")) == ["Mysuru City"]
    assert H._match_places(H._norm("ಮೈಸೂರು")) == ["Mysuru"]


def test_common_crime_heads_have_kannada_names_and_keep_proper_nouns():
    assert display_crime("KARNATAKA_POLICE_ACT_1963", "kn") == "ಕರ್ನಾಟಕ ಪೊಲೀಸ್ ಕಾಯ್ದೆ 1963"
    assert display_crime("Karnataka Police Act 1963", sentence_start=True) == "Karnataka police act 1963"
    assert display_crime("Burglary - Day", "kn") == "ಹಗಲು ಮನೆಗಳ್ಳತನ"


def test_register_stage_spellings_are_one_stage():
    assert CT._stage("Charge_Sheeted") == "CHARGE SHEETED"
    assert CT._STAGES[CT._stage("CHARGE_SHEETED")][0] == "court"
    assert CT._STAGES[CT._stage("UN TRACED")][1] == "Closed as undetected"
    by = CT._by_stage([{"st": "UNDER_INVESTIGATION", "n": 2}, {"st": "UNDER INVESTIGATION", "n": 3}])
    assert by == {"UNDER INVESTIGATION": 5}


def test_alert_lines_have_no_z_score_or_confidence(monkeypatch):
    from app.agents import spikes_answer as S
    import inspect
    src = inspect.getsource(S)
    assert "confidence {round" not in src and "z {float" not in src
