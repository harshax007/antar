import re

# Aadhaar: 12 digits, optional spaces or dashes. A 12-digit run is only an Aadhaar number
# when its Verhoeff check digit is valid and it starts 2-9 (UIDAI never issues 0/1), or when
# the text calls it one just before it ("Aadhaar ...", "UID ...", "ಆಧಾರ್ ...") - an officer's
# label wins over a typo. Before this, every 12-digit case or crime number was redacted.
AADHAAR_PATTERN = re.compile(r'(?<!\d)(?:\d[ -]?){11}\d(?!\d)')
AADHAAR_LABEL = re.compile(r'(aadhaa?r|\buid\b|ಆಧಾರ್)', re.I)
# Phone: an Indian mobile number - optional +91 / 91 / 0, then 10 digits starting 6-9.
# A 10-digit amount or reference that starts 1-5 is not a phone number.
PHONE_PATTERN = re.compile(
    r'(?<![\d@])(?:\+?91[ -]?|0)?([6-9](?:[ -]?\d){5}[ -]?(\d[ -]?\d[ -]?\d[ -]?\d))(?![\d@])')
# UPI VPA (name@bank, no dot after the @ - an email has one): the whole id is personal.
UPI_PATTERN = re.compile(r'\b[A-Za-z0-9._-]{2,}@([A-Za-z][A-Za-z0-9]{1,})\b(?![.\w])')
# Bank account: 9-18 digits named as one ("a/c", "account no") or written beside an IFSC.
ACCOUNT_PATTERN = re.compile(
    r'(?i)(\b(?:a/c|ac|acc(?:ount)?)(?:\s*(?:no|number|num))?\.?\s*[:#-]?\s*)(\d{9,18})\b'
    r'|\b(\d{9,18})(?=\s*,?\s*(?:ifsc\s*[:#-]?\s*)?[A-Z]{4}0[A-Z0-9]{6}\b)')

_VERHOEFF_D = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],
               [4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],[6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],
               [8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]]
_VERHOEFF_P = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],
               [9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],[2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]


def verhoeff_ok(digits: str) -> bool:
    """The Verhoeff checksum UIDAI uses for the last digit of an Aadhaar number."""
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0

EMAIL_PATTERN = re.compile(r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b')
# PAN: 5 letters, 4 digits, 1 letter; the 4th letter is the holder type (P, C, H, F, …)
PAN_PATTERN = re.compile(r'\b[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]\b')

# Case identifiers that must SURVIVE redaction.
#
# The phone pattern matches any 10-digit run with dashes in it, and an FIR number is
# exactly that: "SYN-2026-908137" -> digits 2026908137 -> rewritten to
# "SYN[PHONE:XXXXXX8137]". Traces, audit rows and citations were storing mangled case
# numbers, which defeats the point of a replayable derivation — the officer cannot look
# the FIR up. These shapes are case references, never personal contact details, so they
# are masked out before redaction and restored afterwards.
#
# Covers: SYN-2026-908137 · 2023-BLR-04412 · FIR-2026-0891 · KA-03-AB-1234 (vehicle)
CASE_ID_PATTERNS = (
    re.compile(r'\b[A-Z]{2,4}-\d{4}-[A-Z0-9-]{3,}\b'),      # SYN-2026-908137, FIR-2026-0891
    re.compile(r'\b\d{4}-[A-Z]{2,4}-[A-Z0-9-]{3,}\b'),      # 2023-BLR-04412
    re.compile(r'\b[A-Z]{2}-\d{2}-[A-Z]{1,2}-\d{2,4}\b'),   # KA-03-AB-1234
)
_CASE_TOKEN = "\x00CASE{}\x00"


def _mask_case_ids(text: str) -> tuple[str, list[str]]:
    """Swap case identifiers for placeholders that no PII pattern can match."""
    held: list[str] = []

    def _hold(m):
        held.append(m.group(0))
        return _CASE_TOKEN.format(len(held) - 1)

    for pat in CASE_ID_PATTERNS:
        text = pat.sub(_hold, text)
    return text, held


def _restore_case_ids(text: str, held: list[str]) -> str:
    for i, original in enumerate(held):
        text = text.replace(_CASE_TOKEN.format(i), original)
    return text


def redact_pii(text: str) -> str:
    """
    Redacts sensitive PII (Aadhaar, Phone Numbers) leaving only the last 4 digits.
    Case/FIR/vehicle identifiers are preserved — they are evidence references, not PII.
    """
    if not text:
        return text

    text, held = _mask_case_ids(text)

    # Email first (it has a dot after the @; keep the domain - "a gmail account" - drop the
    # person), then UPI ids, so neither is half-masked as a phone number.
    text = EMAIL_PATTERN.sub(lambda m: f"[EMAIL:***@{m.group(2)}]", text)
    text = UPI_PATTERN.sub(lambda m: f"[UPI:***@{m.group(1)}]", text)

    # Bank account named as one, or beside an IFSC ([ACCOUNT:XXXX4567]); the IFSC itself is a
    # branch code, not personal, and stays.
    def _account_repl(m):
        num = m.group(2) or m.group(3)
        return f"{m.group(1) or ''}[ACCOUNT:XXXX{num[-4:]}]"

    text = ACCOUNT_PATTERN.sub(_account_repl, text)

    # Aadhaar (XXXX-XXXX-1234): checksum-valid, or labelled as Aadhaar just before it
    def _aadhaar_repl(m):
        digits = re.sub(r'\D', '', m.group(0))
        labelled = bool(AADHAAR_LABEL.search(text[max(0, m.start() - 60):m.start()]))
        if labelled or (digits[0] in "23456789" and verhoeff_ok(digits)):
            return f"[AADHAAR:XXXX-XXXX-{digits[-4:]}]"
        return m.group(0)

    text = AADHAAR_PATTERN.sub(_aadhaar_repl, text)

    # Indian mobile number ([PHONE:XXXXXX1234])
    text = PHONE_PATTERN.sub(lambda m: f"[PHONE:XXXXXX{re.sub(r'[^0-9]', '', m.group(2))}]", text)
    # PAN (Income Tax): AAAAA9999A -> keep the last 4, like Aadhaar and phone.
    text = PAN_PATTERN.sub(lambda m: f"[PAN:XXXXXX{m.group(0)[-4:]}]", text)

    return _restore_case_ids(text, held)

def evaluate_bias(profile_text: str) -> dict:
    """
    Evaluates generated profile text for potentially biased terminology.
    Returns {"anti_bias_cleared": bool, "bias_warnings": list}.
    """
    if not profile_text:
        return {"anti_bias_cleared": True, "bias_warnings": []}
        
    profile_lower = profile_text.lower()
    warnings = []
    
    # Example restricted terms that should not influence risk scoring
    # In a real 100M system, this would be a large loaded dictionary
    restricted_terms = ["caste", "dalit", "brahmin", "muslim", "hindu", "christian", "slum-dweller", "illiterate"]
    
    for term in restricted_terms:
        if term in profile_lower:
            warnings.append(f"Flagged restricted demographic term: '{term}'")
            
    return {
        "anti_bias_cleared": len(warnings) == 0,
        "bias_warnings": warnings
    }

def calculate_shap_values(factors: dict, weights: dict) -> dict:
    """
    Computes SHAP-like mathematical feature attributions for the risk score.
    Since our risk model is linear additive: score = 100 * sum(w_i * f_i),
    the SHAP attribution of feature i is exactly 100 * w_i * f_i.
    """
    return {k: round(weights[k] * factors[k] * 100, 2) for k in factors if k in weights}
