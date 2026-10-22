"""Kannada and Indian-name spelling: a Kannada question reaches the English FIR text, and
a name finds its other spellings - without matching a different name."""
import pytest

from app.core.kn_translit import kn_to_latin
from app.second_brain.kn_query import to_english
from app.services.indic_names import name_key, same_name


@pytest.mark.parametrize("kn,latin", [
    ("ಸುರೇಶ್", "suresh"), ("ಯಲ್ಲಪ್ಪ", "yallappa"), ("ಜಕ್ಕನಹಳ್ಳಿ", "jakkanahalli"),
    ("ಶಂಕರ್", "shankar"), ("ಲಕ್ಷ್ಮಿ", "lakshmi"), ("Suresh", "Suresh"),
])
def test_kannada_to_latin(kn, latin):
    assert kn_to_latin(kn) == latin


@pytest.mark.parametrize("a,b", [
    ("Suresh", "Suresha"), ("Krishnamurthy", "Krsnamurti"), ("Mohammed", "Muhammed"), ("Mohammed", "Mohd"),
    ("Yellappa", "Elappa"), ("Venkatesh", "Wenkatesh"), ("Chandrashekar", "Chandrasekhar"),
    ("Jayaram", "Jairam"), ("Kumar", "Coomar"), ("Gowda", "Gouda"), ("Lakshmi", "Laxmi"),
    ("Shivakumar", "Sivakumar"), ("Basavaraj", "Baswaraj"), ("Ramaiah", "Ramayya"),
    ("ಸುರೇಶ್", "Suresh"), ("ಯಲ್ಲಪ್ಪ", "Yellappa"), ("ಬಸವರಾಜ್", "Basavaraj"), ("ಮಂಜುನಾಥ", "Manjunath"),
])
def test_one_name_spelt_two_ways(a, b):
    assert same_name(a, b), (name_key(a), name_key(b))


@pytest.mark.parametrize("a,b", [
    ("Suresh", "Ramesh"), ("Raju", "Ravi"), ("Kumar", "Kiran"), ("Manju", "Manoj"), ("Prakash", "Prasad"),
    ("Mahesh", "Mukesh"), ("Rajesh", "Rakesh"), ("Ganesh", "Dinesh"), ("Naveen", "Praveen"), ("Anil", "Sunil"),
])
def test_different_names_stay_apart(a, b):
    assert not same_name(a, b), (name_key(a), name_key(b))


def test_name_search_takes_kannada_and_spelling_variants():
    from app.services.entity_resolver import fuzzy_match_suspects
    world = {"suspects": [
        {"suspect_id": "S1", "full_name": "Yellappa M.", "alias": "", "father_name": ""},
        {"suspect_id": "S2", "full_name": "Deepak Kumar", "alias": "", "father_name": ""},
        {"suspect_id": "S3", "full_name": "Ramesh Rao", "alias": "", "father_name": ""},
    ]}
    ids = lambda q: [h["suspect_id"] for h in fuzzy_match_suspects(q, world, threshold=0.82)]
    assert ids("ಯಲ್ಲಪ್ಪ") == ["S1"] and ids("Elappa") == ["S1"] and ids("Coomar") == ["S2"]
    assert "S3" not in ids("Suresh")


@pytest.mark.parametrize("kn,en", [
    ("ಬಸ್ ನಿಲ್ದಾಣದ ಬಳಿ ಸರಗಳ್ಳತನ", "bus stand near chain snatching"),
    ("ರಾತ್ರಿ ಮನೆ ಕಳ್ಳತನ", "night house theft"),
    ("ದೇವಸ್ಥಾನದಲ್ಲಿ ಚಿನ್ನದ ಸರ ಕಳ್ಳತನ", "temple gold chain theft"),
    ("ಜಕ್ಕನಹಳ್ಳಿಯಲ್ಲಿ ಬೈಕ್ ಕಳ್ಳತನ", "jakkanahalli two wheeler theft"),
    ("chain snatching near bus stand", "chain snatching near bus stand"),
])
def test_a_kannada_question_reaches_the_english_record(kn, en):
    assert to_english(kn) == en


def test_full_name_outranks_one_word_and_father_and_ids_are_found():
    from app.services.entity_resolver import fuzzy_match_suspects
    world = {"suspects": [
        {"suspect_id": "S1", "full_name": "Lokesh Murthy", "alias": "", "father_name": ""},
        {"suspect_id": "S2", "full_name": "Shivu Nayak", "alias": "", "father_name": "Lokesh Desai"},
        {"suspect_id": "S3", "full_name": "Lokesh Desai", "alias": "", "father_name": ""},
        {"suspect_id": "S4", "full_name": "Ravi S.", "alias": "", "father_name": ""},
    ]}
    hits = fuzzy_match_suspects("Lokesh Desai", world, threshold=0.55)
    assert [h["suspect_id"] for h in hits[:2]] == ["S3", "S2"]          # own name, then father's
    assert hits[-1]["suspect_id"] == "S1"                               # one word of two, last
    ids = fuzzy_match_suspects("S4", world, threshold=0.82)
    assert ids and ids[0]["suspect_id"] == "S4" and ids[0]["match_method"] == "id_exact"
    assert "S4" not in [h["suspect_id"] for h in fuzzy_match_suspects("S1063", world, threshold=0.82)]
