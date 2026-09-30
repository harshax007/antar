"""
Antar — Shared display-name helpers (sentence case, crime names, direction words)
==================================================================================
One place to normalise database labels into human-readable text for both English
and Kannada.  Used by answer_writer, followup_agent, layout_composer, and the
profile_agent MO summary.

Rules (from fixPlan.md §2):
  • Inside a sentence:   " CYBER CRIME" → "cyber crime"
  • At sentence start:   " CYBER CRIME" → "Cyber crime"
  • In KN:               " CYBER CRIME" → "ಸೈಬರ್ ಅಪರಾಧ"
  • Direction:            "UPWARD" → "Rising" (EN) / "ಏರಿಕೆ" (KN)
  • Dimension:            "zone" → "districts" (when data is district-level)
"""

from __future__ import annotations

# Kannada crime name lookup — shared with answer_writer._KN_CRIME
_KN_CRIME = {
    "THEFT": "ಕಳ್ಳತನ", "ROBBERY": "ದರೋಡೆ", "DACOITY": "ಡಕಾಯಿತಿ", "BURGLARY": "ಮನೆಗಳ್ಳತನ",
    "HOUSE BREAKING": "ಮನೆಗಳ್ಳತನ", "CHAIN SNATCHING": "ಸರಗಳ್ಳತನ", "MURDER": "ಕೊಲೆ",
    "ATTEMPT TO MURDER": "ಕೊಲೆ ಯತ್ನ", "CHEATING": "ವಂಚನೆ", "CYBER CRIME": "ಸೈಬರ್ ಅಪರಾಧ",
    "CHEATING FRAUD": "ವಂಚನೆ", "DOMESTIC VIOLENCE": "ಕೌಟುಂಬಿಕ ಹಿಂಸೆ",
    "MISSING PERSON": "ಕಾಣೆಯಾದ ವ್ಯಕ್ತಿ", "CASES OF HURT": "ಹಲ್ಲೆ",
    "MOTOR VEHICLE ACCIDENTS FATAL": "ಮಾರಣಾಂತಿಕ ರಸ್ತೆ ಅಪಘಾತ",
    "MOTOR VEHICLE ACCIDENTS NON-FATAL": "ರಸ್ತೆ ಅಪಘಾತ (ಮಾರಣಾಂತಿಕವಲ್ಲದ)",
    "VEHICLE THEFT": "ವಾಹನ ಕಳ್ಳತನ", "RAPE": "ಅತ್ಯಾಚಾರ", "KIDNAPPING AND ABDUCTION": "ಅಪಹರಣ",
    "NDPS": "ಮಾದಕ ವಸ್ತು (NDPS)", "RIOTS": "ಗಲಭೆ", "PUBLIC SAFETY": "ಸಾರ್ವಜನಿಕ ಸುರಕ್ಷತೆ",
    "DOWRY": "ವರದಕ್ಷಿಣೆ",
}

# Direction words
_DIR_EN = {"UPWARD": "Rising", "DOWNWARD": "Falling", "STABLE": "Steady"}
_DIR_KN = {"UPWARD": "ಏರಿಕೆ", "DOWNWARD": "ಇಳಿಕೆ", "STABLE": "ಸ್ಥಿರ"}

# Dimension display names
_DIM_EN = {"zone": "districts", "district": "districts", "station_code": "police stations",
           "station": "police stations", "city": "cities"}
_DIM_KN = {"zone": "ಜಿಲ್ಲೆಗಳು", "district": "ಜಿಲ್ಲೆಗಳು", "station_code": "ಠಾಣೆಗಳು",
           "station": "ಠಾಣೆಗಳು", "city": "ನಗರಗಳು"}

# Acronyms that stay uppercase even in sentence case
_ACRONYMS = {"FIR", "UPI", "IP", "KSP", "BNS", "OSINT", "NDPS", "POCSO", "SC", "ST"}


def _normalise(raw: str) -> str:
    """Trim, collapse spaces, and treat underscores as spaces.

    The seeded rows spell groups as identifiers ("CHAIN_SNATCHING"). Left as-is they
    rendered as "Chain_snatching" in English, and missed the Kannada table — which is
    keyed "CHAIN SNATCHING" — so Kannada answers printed the raw English identifier.
    """
    return " ".join(str(raw or "").replace("_", " ").split()).strip().upper()


def display_crime(name: str | None, lang: str = "en", *, sentence_start: bool = False) -> str:
    """Convert a raw CrimeGroup_Name to display form.

    - EN inside sentence: "cyber crime", "theft", "NDPS"
    - EN at sentence start: "Cyber crime", "Theft", "NDPS"
    - KN: returns the Kannada name from _KN_CRIME, or the EN form if no translation.
    """
    key = _normalise(name)
    if not key:
        return "crime" if lang != "kn" else "ಅಪರಾಧ"

    if lang == "kn":
        return _KN_CRIME.get(key) or _to_sentence(key)

    # English: sentence case with acronym preservation
    return _to_sentence(key, capitalize=sentence_start)


def display_direction(raw: str | None, lang: str = "en") -> str:
    """UPWARD/DOWNWARD/STABLE → Rising/Falling/Steady (EN) or Kannada equiv."""
    key = _normalise(raw)
    if lang == "kn":
        return _DIR_KN.get(key, key)
    return _DIR_EN.get(key, key)


def display_dimension(dim: str | None, lang: str = "en") -> str:
    """zone/district/station_code → 'districts' / 'police stations' etc."""
    key = (dim or "").strip().lower()
    if lang == "kn":
        return _DIM_KN.get(key, key)
    return _DIM_EN.get(key, key)


def _to_sentence(s: str, *, capitalize: bool = False) -> str:
    """Convert UPPERCASE text to sentence case, preserving known acronyms."""
    words = s.split()
    out = []
    for i, w in enumerate(words):
        if w in _ACRONYMS:
            out.append(w)
        elif i == 0 and capitalize:
            out.append(w.capitalize())
        else:
            lower = w.lower()
            # Keep small words lowercase even at start in sentence context
            if i > 0 and lower in ("of", "and", "the", "in", "by", "to", "vs"):
                out.append(lower)
            elif i == 0:
                out.append(w.capitalize() if capitalize else lower)
            else:
                out.append(lower)
    return " ".join(out)
"""
New shared module for display names. Consolidates crime type, direction, and
dimension display logic so answer_writer, followup_agent, and the frontend
chips all use the same human-readable labels. No ALL-CAPS crime names in
answers or chips.
"""
