from app.core.guardrails import redact_pii, evaluate_bias
from app.services.quickml import quickml_generate
import pytest

def test_redact_pii_aadhaar():
    text = "Suspect Aadhaar is 1234 5678 9012 and another 1234-5678-9012"
    redacted = redact_pii(text)
    assert "[AADHAAR:XXXX-XXXX-9012]" in redacted
    assert "1234" not in redacted
    assert "5678" not in redacted

def test_redact_pii_phone():
    text = "Call me at +91 9876543210 or 09876543210."
    redacted = redact_pii(text)
    assert "[PHONE:XXXXXX3210]" in redacted
    assert "98765" not in redacted

def test_evaluate_bias_clean():
    profile = "Suspect has 5 prior arrests for chain snatching in Rajajinagar."
    res = evaluate_bias(profile)
    assert res["anti_bias_cleared"] is True
    assert len(res["bias_warnings"]) == 0

def test_evaluate_bias_flagged():
    profile = "Suspect is a slum-dweller with a history of theft."
    res = evaluate_bias(profile)
    assert res["anti_bias_cleared"] is False
    assert len(res["bias_warnings"]) == 1
    assert "slum-dweller" in res["bias_warnings"][0]


@pytest.mark.parametrize("text,gone,kept", [
    ("Aadhaar 2341 2341 2346 of the complainant", "2341 2341", "[AADHAAR:XXXX-XXXX-2346]"),
    ("complainant id 2341 2341 2346 noted", "2341 2341", "[AADHAAR:XXXX-XXXX-2346]"),    # checksum-valid, unlabelled
    ("paid to 9845012345@ybl", "9845012345", "[UPI:***@ybl]"),                           # whole UPI id, not half
    ("a/c 30881234567 SBIN0040071", "30881234567", "[ACCOUNT:XXXX4567] SBIN0040071"),    # IFSC is a branch code, kept
    ("Account No: 123456789012 at SBI", "123456789012", "[ACCOUNT:XXXX9012]"),
    ("ph: 98450-67890", "98450-67890", "[PHONE:XXXXXX7890]"),
])
def test_personal_identifiers_are_caught(text, gone, kept):
    out = redact_pii(text)
    assert gone not in out and kept in out


@pytest.mark.parametrize("text", [
    "Crime No 2023 0012 3456 registered",      # 12 digits, fails Verhoeff, not labelled Aadhaar
    "Ref 202300123456 at Rajajinagar",
    "FIR 1000151202200051 filed",              # 16-digit FIR number
    "Amount 1234567890 paid",                  # 10 digits, but no mobile starts with 1
    "IMEI 490154203237518 seized",             # evidence reference, like a vehicle number
    "vehicle KA-03-AB-1234 at 12:30",
    "date 2023-10-12 time 22:15",
])
def test_case_numbers_and_evidence_references_are_not_redacted(text):
    assert redact_pii(text) == text
