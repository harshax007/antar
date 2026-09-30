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
