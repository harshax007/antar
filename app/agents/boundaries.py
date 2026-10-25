"""
Antar - what the system will not do, said where it is asked
===========================================================
Some questions ask for something Antar must not give, inside an otherwise answerable
question. The data answer still runs; the boundary is stated first, in one plain line, so
the officer does not read the answer as having done the forbidden part:

  guilt     "can this AI establish the guilt of S0001?" - an FIR count is an investigative
            lead, never a finding of guilt; only a court decides that.
  minors    "minor victims with their names and home addresses" - a child victim's identity
            is never disclosed (POCSO Act s.23, JJ Act s.74); the register holds victims by
            sex and age group only.
  victims   names / addresses / phone numbers of victims or complainants - not shown in chat.

Deterministic, no model. Each note is one line; the answer below it is unchanged.
"""
from __future__ import annotations

import re

# Asking whether someone IS guilty, not a count of convictions ("conviction rate" is data).
_GUILT = re.compile(r"\b(establish|determine|prove|decide|confirm|declare|say|tell|know)\w*\b[^.?!]{0,50}\b(guilt|guilty|committed (?:it|the crime))\b"
                    r"|\bis\s+\S+(?:\s+\S+)?\s+guilty\b|\bguilt of\b|\bwho (?:is|was) guilty\b", re.I)
_MINOR = re.compile(r"\b(minors?|child(?:ren)?|juveniles?|under\s*18|below\s*18|girls?|boys?|pocso)\b", re.I)
# "phone numbers", not "phone theft"; "names", not the crime the victim suffered
_IDENTITY = re.compile(r"\b(names?|home address\w*|address\w*|(?:phone|mobile|contact) (?:numbers?|nos?|details)|"
                       r"photos?|photographs?|school|identit\w*|identify them)\b", re.I)
_VICTIM = re.compile(r"\b(victims?|complainants?|survivors?)\b", re.I)


def notes(text: str, lang: str = "en") -> list[str]:
    t = text or ""
    kn = lang == "kn"
    out: list[str] = []
    if _GUILT.search(t):
        out.append("ಗಮನಿಸಿ: Antar ಯಾರ ತಪ್ಪನ್ನೂ ನಿರ್ಧರಿಸುವುದಿಲ್ಲ. FIR ದಾಖಲೆಗಳು ತನಿಖೆಯ ಸುಳಿವುಗಳು ಮಾತ್ರ; ತಪ್ಪು ಅಥವಾ ಶಿಕ್ಷೆಯನ್ನು ನ್ಯಾಯಾಲಯ ಮಾತ್ರ ನಿರ್ಧರಿಸುತ್ತದೆ." if kn else
                   "Antar cannot establish guilt. Linked FIRs are investigative leads; guilt is decided only by a court, "
                   "on evidence tested at trial. Below is what the register records, not a finding.")
    if _VICTIM.search(t) or _MINOR.search(t):
        if _IDENTITY.search(t):
            if _MINOR.search(t):
                out.append("ಮಕ್ಕಳ ಸಂತ್ರಸ್ತರ ಹೆಸರು, ವಿಳಾಸ ಅಥವಾ ಗುರುತು ತೋರಿಸಲಾಗುವುದಿಲ್ಲ (POCSO ಕಾಯ್ದೆ ಸೆ.23, JJ ಕಾಯ್ದೆ ಸೆ.74)." if kn else
                           "A child victim's name, address or anything that identifies them is never shown (POCSO Act s.23, "
                           "JJ Act s.74). The register records victims by sex and age group only; counts are below.")
            else:
                out.append("ಸಂತ್ರಸ್ತರು ಮತ್ತು ದೂರುದಾರರ ಹೆಸರು ಮತ್ತು ವಿಳಾಸವನ್ನು ಚಾಟ್‌ನಲ್ಲಿ ತೋರಿಸಲಾಗುವುದಿಲ್ಲ." if kn else
                           "Victims' and complainants' names, addresses and phone numbers are not shown in chat; the register "
                           "records victims by sex and age group only.")
    return out


def prefix(answer: str, text: str, lang: str = "en") -> str:
    n = notes(text, lang)
    if not n:
        return answer
    return "\n".join(n) + "\n\n" + (answer or "")
