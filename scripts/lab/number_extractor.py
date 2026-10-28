"""
Number extractor for BIRD-style execution accuracy evaluation (Phase L4).
Extracts numbers from LLM/agent responses, supporting:
- Indian comma grouping: 1,23,456
- Western comma grouping: 123,456
- Percentages: 0.6%, 40.4%
- Words: 19.2 lakh, 1.5 crore
- Ignores: dates (2024-03-31), years (2016-2026), ordinals (1., 2.), FIR/Case IDs, sections
"""
import re
from decimal import Decimal
from typing import List


def extract_numbers(text: str) -> List[Decimal]:
    if not text:
        return []
    
    # 1. Mask known non-quantity patterns to avoid false matches
    
    # Mask ISO dates: 2024-03-31, 2024/03/31
    cleaned = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", text)
    
    # Mask textual dates: e.g. 17 Feb 2024, 20 January 2023
    cleaned = re.sub(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", " ", cleaned, flags=re.I)
    
    # Mask FIR IDs / Long serials: e.g. 100351090202400015, C242196, FIR-2024-1234
    cleaned = re.sub(r"\b(?:FIR\s+)?\d{10,20}\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\b[A-Z]{1,4}[-_]?\d{4,10}\b", " ", cleaned)
    
    # Mask Sections: U/s 379, Sec 420, Section 34
    cleaned = re.sub(r"(?i)\b(?:u/s|sec(?:tion)?)\s*[:.]?\s*\d+(?:\([a-z0-9]+\))?", " ", cleaned)
    
    # Mask List Ordinals at start of line or after newline: "1. ", "2. ", "10. "
    cleaned = re.sub(r"(?:^|\n)\s*\d{1,2}\.\s+", "\n ", cleaned)
    
    # Mask standalone years (2016 - 2026) when preceded by "in", "year", "since", etc. or standalone
    cleaned = re.sub(r"\b(?:in|year|during|of|since)?\s*(201[6-9]|202[0-6])\b", " ", cleaned, flags=re.I)
    
    results: List[Decimal] = []
    
    # 2. Extract lakh / crore expressions: e.g. "19.2 lakh", "1.5 crore", "10 lakhs"
    lakh_crore_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)\b", re.I)
    for match in lakh_crore_pattern.finditer(cleaned):
        val = Decimal(match.group(1))
        unit = match.group(2).lower()
        if "lakh" in unit:
            results.append(val * Decimal(100000))
        elif "crore" in unit:
            results.append(val * Decimal(10000000))
    # Remove the matched lakh/crore substrings so they aren't parsed twice
    cleaned = lakh_crore_pattern.sub(" ", cleaned)
    
    # 3. Extract percentages: e.g. "0.6%", "40.4%", "12%"
    pct_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*%")
    for match in pct_pattern.finditer(cleaned):
        results.append(Decimal(match.group(1)))
    cleaned = pct_pattern.sub(" ", cleaned)
    
    # 4. Extract remaining numeric tokens (including comma-grouped ints & decimals)
    # Handles 1,23,456 (Indian) and 123,456 (Western)
    num_pattern = re.compile(r"(?<![A-Za-z0-9_])(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?![A-Za-z0-9_])")
    for match in num_pattern.finditer(cleaned):
        raw = match.group(1).replace(",", "")
        try:
            d = Decimal(raw)
            results.append(d)
        except Exception:
            pass
            
    return results
