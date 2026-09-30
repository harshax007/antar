import re

# Aadhaar: 12 digits, optional spaces or dashes
AADHAAR_PATTERN = re.compile(r'\b(?:\d[ -]*?){8}(\d[ -]*?\d[ -]*?\d[ -]*?\d)\b')
# Phone: +91 or 0 followed by 10 digits, or just 10 digits
PHONE_PATTERN = re.compile(r'\b(?:\+?91|0)?\s*[ -]*?(?:\d\s*[ -]*?){6}(\d\s*[ -]*?\d\s*[ -]*?\d\s*[ -]*?\d)\b')

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

    # Redact Aadhaar (XXXX-XXXX-1234)
    # The regex captures the last 4 digits in group 1
    def _aadhaar_repl(match):
        last_4 = match.group(1).replace(' ', '').replace('-', '')
        return f"[AADHAAR:XXXX-XXXX-{last_4}]"

    text = AADHAAR_PATTERN.sub(_aadhaar_repl, text)

    # Redact Phone ([PHONE:XXXXXX1234])
    def _phone_repl(match):
        last_4 = match.group(1).replace(' ', '').replace('-', '')
        return f"[PHONE:XXXXXX{last_4}]"

    text = PHONE_PATTERN.sub(_phone_repl, text)

    # Email: keep the domain (useful for an analyst — "a gmail account"), drop the person.
    text = EMAIL_PATTERN.sub(lambda m: f"[EMAIL:***@{m.group(2)}]", text)
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
