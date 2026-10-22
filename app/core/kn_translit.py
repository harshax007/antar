"""
Antar — Kannada script to Latin letters
=======================================
The FIR register spells names and places in Latin letters ("Suresh", "Jakkanahalli"); an
officer may type them in Kannada (ಸುರೇಶ್, ಜಕ್ಕನಹಳ್ಳಿ). This turns Kannada script into the
plain Latin spelling an officer would write, so the name search and the Brain can compare
like with like. It is not a scholarly transliteration (no diacritics): long vowels are
doubled (ಆ -> aa) and the name matcher folds those away again.

Rules of the script, in short: a consonant carries an inherent "a" unless a vowel sign
or the virama (್) follows it; vowel signs replace that "a"; the anusvara (ಂ) is "m"
before p/b/m and "n" otherwise. Non-Kannada text passes through unchanged.
"""

from __future__ import annotations

_CONS = {
    "ಕ": "k", "ಖ": "kh", "ಗ": "g", "ಘ": "gh", "ಙ": "n",
    "ಚ": "ch", "ಛ": "chh", "ಜ": "j", "ಝ": "jh", "ಞ": "n",
    "ಟ": "t", "ಠ": "th", "ಡ": "d", "ಢ": "dh", "ಣ": "n",
    "ತ": "t", "ಥ": "th", "ದ": "d", "ಧ": "dh", "ನ": "n",
    "ಪ": "p", "ಫ": "ph", "ಬ": "b", "ಭ": "bh", "ಮ": "m",
    "ಯ": "y", "ರ": "r", "ಱ": "r", "ಲ": "l", "ವ": "v",
    "ಶ": "sh", "ಷ": "sh", "ಸ": "s", "ಹ": "h", "ಳ": "l", "ೞ": "l",
}
_VOWELS = {
    "ಅ": "a", "ಆ": "aa", "ಇ": "i", "ಈ": "ee", "ಉ": "u", "ಊ": "oo", "ಋ": "ru",
    "ಎ": "e", "ಏ": "e", "ಐ": "ai", "ಒ": "o", "ಓ": "o", "ಔ": "au",
}
_SIGNS = {
    "ಾ": "aa", "ಿ": "i", "ೀ": "ee", "ು": "u", "ೂ": "oo", "ೃ": "ru",
    "ೆ": "e", "ೇ": "e", "ೈ": "ai", "ೊ": "o", "ೋ": "o", "ೌ": "au",
}
_VIRAMA, _ANUSVARA, _VISARGA = "್", "ಂ", "ಃ"
_ZW = dict.fromkeys((0x200C, 0x200D, 0x200B), None)    # ZWNJ / ZWJ / ZWSP
_DIGITS = {chr(0x0CE6 + i): str(i) for i in range(10)}


def has_kannada(text: str) -> bool:
    return any("ಀ" <= ch <= "೿" for ch in text or "")


def kn_to_latin(text: str) -> str:
    """ಸುರೇಶ್ -> suresh, ಯಲ್ಲಪ್ಪ -> yallappa, ಜಕ್ಕನಹಳ್ಳಿ -> jakkanahalli. Lower case."""
    if not has_kannada(text):
        return text
    s = (text or "").translate(_ZW)
    out: list[str] = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if ch in _CONS:
            out.append(_CONS[ch])
            if nxt in _SIGNS:
                out.append(_SIGNS[nxt]); i += 2; continue
            if nxt == _VIRAMA:
                i += 2; continue
            out.append("a")                     # the inherent vowel
        elif ch in _VOWELS:
            out.append(_VOWELS[ch])
        elif ch == _ANUSVARA:
            follow = s[i + 1] if i + 1 < n else ""
            out.append("m" if _CONS.get(follow, "")[:1] in ("p", "b", "m") else "n")
        elif ch == _VISARGA:
            out.append("h")
        elif ch in _DIGITS:
            out.append(_DIGITS[ch])
        elif ch in _SIGNS or ch == _VIRAMA:
            pass                                # a stray sign with no consonant before it
        else:
            out.append(ch)
        i += 1
    return "".join(out).lower()
