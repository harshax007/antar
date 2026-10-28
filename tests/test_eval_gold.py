"""
Tests for extract_numbers (Phase L4).
"""
from decimal import Decimal
from scripts.lab.number_extractor import extract_numbers


def test_extract_basic_integers_and_commas():
    text = "Bengaluru City registered **40,736** theft cases with **1,040,002** total FIRs."
    nums = extract_numbers(text)
    assert Decimal("40736") in nums
    assert Decimal("1040002") in nums


def test_extract_percentages():
    text = "The conviction rate for theft in Bengaluru City is **0.6%**."
    nums = extract_numbers(text)
    assert Decimal("0.6") in nums


def test_extract_lakhs_and_crores():
    text = "Karnataka registered approximately 19.2 lakh FIRs, while statewide loss reached 2.5 crore rupees."
    nums = extract_numbers(text)
    assert Decimal("1920000") in nums
    assert Decimal("25000000") in nums


def test_ignores_dates_and_serials_and_ordinals():
    text = """
    On 2024-02-17, FIR 100351090202400015 was filed under Section 379 in year 2024.
    Latest FIRs:
    1. FIR C242196 — 17 Feb 2024
    2. FIR C11707 — 20 Jan 2023
    Total verified cases: **16**
    """
    nums = extract_numbers(text)
    # 2024-02-17, 100351090202400015, 379, 2024, 1., 2. should be ignored
    assert Decimal("16") in nums
    assert Decimal("379") not in nums
    assert Decimal("2024") not in nums
    assert Decimal("100351090202400015") not in nums
