"""
Antar — How Indian names are spelt in Latin letters
===================================================
American Soundex keys on the first letter and on English consonant groups, so it misses
the variation that is ordinary in a Karnataka register: Kumar / Coomar, Venkatesh /
Wenkatesh, Yellappa / Elappa, Mohd / Mohammed, Lakshmi / Laxmi, Suresh / Suresha.

`name_key()` folds those spellings into one key. Two tokens are the same name when their
keys are equal, or near-equal by Jaro-Winkler (KEY_JW) - that catches the rest
(Basavaraj / Baswaraj, Mohammed / Muhammed). Kannada script is converted first, so ಸುರೇಶ್
meets Suresh.

It is a matching aid, not a judgment: a key match says two spellings could be the same
name. The search screen shows the record; the officer decides whether it is the person.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.core.kn_translit import kn_to_latin

# Abbreviations and honorifics written several ways. Whole tokens only.
_ABBREV = {
    "mohd": "mohammed", "md": "mohammed", "mohd.": "mohammed", "mhd": "mohammed",
    "sk": "shaikh", "shk": "shaikh", "sheikh": "shaikh", "shaik": "shaikh",
    "syd": "syed", "sayed": "syed", "saiyad": "syed", "sayyed": "syed",
    "shri": "sri", "sree": "sri", "shree": "sri",
}
KEY_JW = 0.9   # keys this close are treated as the same spelling of a name...
SHORT = 6      # ...but keys shorter than this must be equal (Manju is not Manoj)

# Ordered rewrites; each is a regular expression on the lower-cased token.
_RULES = [
    (r"^y[ae](?=[^aeiou])", "e"),     # Yellappa / Ellappa; ಯಲ್ಲಪ್ಪ reads "yallappa"
    (r"ph", "f"),
    (r"q", "k"),
    (r"x", "ks"),                     # Laxmi / Lakshmi
    (r"z", "j"),                      # Zaheer / Jaheer
    (r"ck", "k"),
    (r"ch", "C"),                     # keep "ch" while c becomes k
    (r"c", "k"),                      # Coomar / Kumar
    (r"C", "ch"),
    (r"ou|ow(?=[^aeiou]|$)", "u"),    # Gouda / Gowda / Guda
    (r"w", "v"),                      # Wenkatesh / Venkatesh
    (r"([kgtdpbcj])h", r"\1"),        # aspirates: Bhaskar / Baskar, Dharwad / Darwad
    (r"sh", "s"),                     # Shivakumar / Sivakumar
    (r"aa", "a"), (r"ee|ii", "i"), (r"oo|uu", "u"),
    (r"(.)\1+", r"\1"),               # doubled letters: Yellappa / Yelappa
    (r"aiah$|ayya$|aya$", "ai"),      # Ramaiah / Ramayya
    (r"aya(?=[^aeiou])", "ai"),       # Jayaram / Jairam
    (r"(?<=[^aeiou])a$", ""),         # final a: Suresha / Suresh
    (r"y$", "i"),
]
_RULES = [(re.compile(p), r) for p, r in _RULES]
_NON_ALPHA = re.compile(r"[^a-z]")


@lru_cache(maxsize=50_000)          # the search compares every query token with every record
def name_key(token: str) -> str:
    """A spelling-insensitive key for one name token ('' for nothing usable)."""
    t = kn_to_latin(token or "").lower().strip(" .,")
    t = _ABBREV.get(t, t)
    t = _NON_ALPHA.sub("", t)
    if len(t) < 2:
        return t
    for rx, rep in _RULES:
        t = rx.sub(rep, t)
    return t


def same_name(a: str, b: str) -> bool:
    """True when two name tokens are plausibly one name spelt two ways."""
    from app.services.entity_resolver import jaro_winkler
    ka, kb = name_key(a), name_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    return min(len(ka), len(kb)) >= SHORT and jaro_winkler(ka, kb) >= KEY_JW
