"""
Antar — A Kannada question, in the words the FIR text uses
==========================================================
The Brain's embedder (bge-small-en) and its FIR corpus are English: no FIR in the register
carries Kannada text. A Kannada question ("ಬಸ್ ನಿಲ್ದಾಣದ ಬಳಿ ಸರಗಳ್ಳತನ") therefore landed
nowhere near the records it was about - measured, its best match scored 0.27 against 0.72
for the same question in English, and the hits were unrelated.

`to_english()` rewrites the question word by word before it is embedded:
  * crime, place-type, time and MO words from the vocabulary below (plus the app's
    existing Kannada tables) become their English words;
  * Kannada case endings are tolerated (ನಿಲ್ದಾಣದ, ನಿಲ್ದಾಣದಲ್ಲಿ -> "stand");
  * anything else - a village, a person's name - is spelt in Latin letters, the way the
    register spells it (ಜಕ್ಕನಹಳ್ಳಿ -> jakkanahalli).
English text passes through unchanged. No model, no network: a dictionary and a rule.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.core.kn_translit import has_kannada, kn_to_latin

# What officers say, in the words FIR circumstances are written in.
_MO = {
    # crimes
    "ಸರಗಳ್ಳತನ": "chain snatching", "ಮನೆಗಳ್ಳತನ": "house theft", "ಮನೆ ಕಳ್ಳತನ": "house theft",
    "ವಾಹನ ಕಳ್ಳತನ": "vehicle theft", "ಬೈಕ್ ಕಳ್ಳತನ": "two wheeler theft", "ಕಳ್ಳತನ": "theft",
    "ದರೋಡೆ": "robbery dacoity", "ಸುಲಿಗೆ": "robbery", "ಕೊಲೆ": "murder", "ಕೊಲೆಯತ್ನ": "attempt to murder",
    "ಹಲ್ಲೆ": "assault", "ಗಾಯ": "hurt", "ಅಪಘಾತ": "accident", "ವಂಚನೆ": "cheating fraud", "ಮೋಸ": "cheating",
    "ಸೈಬರ್": "cyber", "ಮಾದಕ ವಸ್ತು": "narcotics", "ಮಾದಕ": "narcotics", "ಗಾಂಜಾ": "ganja",
    "ಅಪಹರಣ": "kidnapping", "ವರದಕ್ಷಿಣೆ": "dowry", "ಕಿರುಕುಳ": "harassment", "ಜೂಜು": "gambling",
    "ಮದ್ಯ": "liquor", "ಬೆಂಕಿ": "fire", "ಬೆದರಿಕೆ": "threat", "ಕಾಣೆ": "missing", "ಆತ್ಮಹತ್ಯೆ": "suicide",
    "ಅತ್ಯಾಚಾರ": "rape", "ದೌರ್ಜನ್ಯ": "atrocity", "ಗಲಭೆ": "rioting",
    # places
    "ಬಸ್ ನಿಲ್ದಾಣ": "bus stand", "ರೈಲು ನಿಲ್ದಾಣ": "railway station", "ನಿಲ್ದಾಣ": "stand station",
    "ಬಸ್": "bus", "ರೈಲು": "railway", "ಮನೆ": "house", "ಅಂಗಡಿ": "shop", "ದೇವಸ್ಥಾನ": "temple",
    "ದೇವಾಲಯ": "temple", "ಮಸೀದಿ": "masjid", "ಚರ್ಚ್": "church", "ಮಾರುಕಟ್ಟೆ": "market", "ಸಂತೆ": "market",
    "ರಸ್ತೆ": "road", "ಹೆದ್ದಾರಿ": "highway", "ಶಾಲೆ": "school", "ಕಾಲೇಜು": "college", "ಬ್ಯಾಂಕ್": "bank",
    "ಎಟಿಎಂ": "atm", "ಆಸ್ಪತ್ರೆ": "hospital", "ಪಾರ್ಕ್": "park", "ಉದ್ಯಾನ": "park", "ಹೋಟೆಲ್": "hotel",
    "ಲಾಡ್ಜ್": "lodge", "ಪೆಟ್ರೋಲ್ ಬಂಕ್": "petrol bunk", "ಜಮೀನು": "land", "ತೋಟ": "garden farm",
    "ಹೊಲ": "field", "ಗ್ರಾಮ": "village", "ಹಳ್ಳಿ": "village", "ನಗರ": "city", "ಕೆರೆ": "lake",
    "ಸೇತುವೆ": "bridge", "ವೃತ್ತ": "circle", "ಕ್ರಾಸ್": "cross", "ಬಡಾವಣೆ": "layout",
    # things
    "ಚಿನ್ನ": "gold", "ಸರ": "chain", "ಮಾಂಗಲ್ಯ": "mangalsutra", "ಆಭರಣ": "jewellery", "ಬೆಳ್ಳಿ": "silver",
    "ಮೊಬೈಲ್": "mobile phone", "ಫೋನ್": "phone", "ಬೈಕ್": "bike", "ದ್ವಿಚಕ್ರ ವಾಹನ": "two wheeler",
    "ವಾಹನ": "vehicle", "ಕಾರು": "car", "ಲಾರಿ": "lorry", "ಆಟೋ": "auto", "ಹಣ": "money", "ನಗದು": "cash",
    "ಪರ್ಸ್": "purse", "ಬ್ಯಾಗ್": "bag", "ಲ್ಯಾಪ್‌ಟಾಪ್": "laptop", "ದನ": "cattle", "ಜಾನುವಾರು": "cattle",
    "ಚಾಕು": "knife", "ಮಚ್ಚು": "machete", "ಬೀಗ": "lock", "ಕಿಟಕಿ": "window", "ಬಾಗಿಲು": "door",
    # people
    "ಮಹಿಳೆ": "woman", "ಹೆಂಗಸು": "woman", "ವೃದ್ಧ": "elderly", "ವೃದ್ಧೆ": "elderly woman",
    "ಮಗು": "child", "ಮಕ್ಕಳು": "children", "ಹುಡುಗಿ": "girl", "ಹುಡುಗ": "boy", "ವಿದ್ಯಾರ್ಥಿ": "student",
    # time and manner
    "ರಾತ್ರಿ": "night", "ಹಗಲು": "day", "ಬೆಳಿಗ್ಗೆ": "morning", "ಮಧ್ಯಾಹ್ನ": "afternoon", "ಸಂಜೆ": "evening",
    "ಬಳಿ": "near", "ಹತ್ತಿರ": "near", "ಮುಂದೆ": "in front of", "ಒಳಗೆ": "inside", "ಮುರಿದು": "broken",
    "ಒಡೆದು": "broken", "ಕಿತ್ತು": "snatched", "ಕಸಿದು": "snatched", "ಕದ್ದು": "stolen",
    "ಪರಾರಿ": "escaped",
    "ಪ್ರಕರಣ": "case",
}
# Words that carry no meaning for a search; dropped rather than spelt out.
_DROP = {"ಮತ್ತು", "ಅಥವಾ", "ಈ", "ಆ", "ಒಂದು", "ಇದು", "ಅದು", "ಇರುವ", "ಆದ", "ಆಗಿದೆ", "ತೋರಿಸಿ",
         "ಹುಡುಕಿ", "ಬಗ್ಗೆ", "ಯಾವುವು", "ಇವೆ", "ಇದೆ", "ಹೇಳಿ", "ನೀಡಿ", "ಕೊಡಿ", "ಏನು"}
_ZWNJ, _ZWJ = chr(0x200C), chr(0x200D)      # joiners Kannada typing inserts inside words
_WORD = re.compile(f"[ಀ-೿{_ZWNJ}{_ZWJ}]+|[^\\sಀ-೿]+")
# Case endings glued to a noun: ಜಕ್ಕನಹಳ್ಳಿಯಲ್ಲಿ = ಜಕ್ಕನಹಳ್ಳಿ + ಯಲ್ಲಿ ("in"). Longest first.
_ENDINGS = sorted(["ಗಳಲ್ಲಿ", "ಯಲ್ಲಿ", "ನಲ್ಲಿ", "ದಲ್ಲಿ", "ರಲ್ಲಿ", "ಲ್ಲಿ", "ಯಿಂದ", "ನಿಂದ", "ದಿಂದ", "ಇಂದ",
                   "ಕ್ಕೆ", "ಗೆ", "ಗಳು", "ಗಳ", "ಯ", "ದ", "ನ"], key=len, reverse=True)
_SIGNS = set("ಾಿೀುೂೃೆೇೈೊೋೌ್")


def _stem(w: str) -> str:
    """Drop one case ending, keeping at least three letters of the word."""
    for e in _ENDINGS:
        if w.endswith(e) and len(w) - len(e) >= 3:
            return w[: -len(e)]
    return w


def _base(kn: str) -> str:
    """A vocabulary word without its final vowel sign, so an inflected form still starts
    with it: ಮೈಸೂರು -> ಮೈಸೂರ matches ಮೈಸೂರಿನಲ್ಲಿ. Only for longer words."""
    return kn[:-1] if len(kn) >= 4 and kn[-1] in _SIGNS else kn


@lru_cache(maxsize=1)
def _vocab() -> list[tuple[str, str]]:
    v: dict[str, str] = {}
    try:                                    # the app's existing tables, where they agree
        from app.services.bhashini import _KN_TO_EN_DICT
        v.update({k: s.lower() for k, s in _KN_TO_EN_DICT.items()})
    except Exception:
        pass
    try:
        from app.agents.heuristics import _KN_BRIDGE, _KN_ZONES
        v.update({k: s.lower() for k, s in _KN_ZONES.items()})
        v.update({k: s for k, s in _KN_BRIDGE.items() if k not in v})
    except Exception:
        pass
    v.update(_MO)                           # MO words win: they are what FIR text says
    # questions are matched with joiners removed, so the vocabulary is too (ಲ್ಯಾಪ್‌ಟಾಪ್)
    v = {k.replace(_ZWNJ, "").replace(_ZWJ, ""): e for k, e in v.items()}
    return sorted(v.items(), key=lambda kv: -len(kv[0]))     # longest first


@lru_cache(maxsize=512)
def to_english(text: str) -> str:
    """A Kannada (or mixed) question in English words; English text is returned as is."""
    if not has_kannada(text or ""):
        return text
    s = text.replace(_ZWNJ, "").replace(_ZWJ, "")
    vocab = _vocab()
    out: list[str] = []
    # multi-word phrases first ("ಬಸ್ ನಿಲ್ದಾಣ", "ಮನೆ ಕಳ್ಳತನ"), with any case ending glued to
    # them, marked so the word pass skips them
    for kn, en in vocab:
        if " " in kn and kn in s:
            s = re.sub(re.escape(kn) + "[ಀ-೿]*", f" \x00{en.replace(' ', '_')}\x00 ", s)
    for w in _WORD.findall(s):
        if w.startswith("\x00") or "\x00" in w:
            out.append(w.strip("\x00").replace("_", " "))
            continue
        if not has_kannada(w):
            out.append(w)
            continue
        if w in _DROP:
            continue
        # the longest vocabulary word this one starts with: ನಿಲ್ದಾಣದ, ನಿಲ್ದಾಣದಲ್ಲಿ -> ನಿಲ್ದಾಣ
        hit = next((en for kn, en in vocab if " " not in kn and len(kn) >= 2
                    and (w.startswith(kn) or w.startswith(_base(kn)))), None)
        out.append(hit if hit else kn_to_latin(_stem(w)))
    return " ".join(o for o in out if o.strip()).strip()
