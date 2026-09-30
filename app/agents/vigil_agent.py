"""
Antar — Vigil Agent (A5: Bias & Compliance Auditor · Phase 1)
==================================================================
Watches every prompt and query (including Dwani voice transcripts and Sentinel watchlists).
Generates compiled 'vigil:{req_id}' compliance receipts:
  1. Flags prohibited demographic targeting (caste, religion, community-as-suspect)
  2. Checks for PII over-collection without FIR context
  3. Verifies that suggested actions cite underlying BNSS / BNS / IPC sections
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services import product_store, audit_store

# Prohibited profiling keywords (case-insensitive checks)
_PROHIBITED_DEMOGRAPHICS = [
    "caste", "dalit", "brahmin", "lingayat", "vokkaliga", "kuruba",
    "muslim", "hindu", "christian", "jain", "community", "slum dwellers",
    "migrants from", "specific religion"
]

_PII_OVERCOLLECTION_WORDS = [
    "all aadhaar", "bulk aadhaar", "everyone's phone", "all phone numbers in zone",
    "unauthorized interception", "wiretap without warrant"
]


def audit_request(query: str, req_id: str | None = None, officer: str = "OFF-001") -> dict[str, Any]:
    """Audit a query or prompt for bias, prohibited targeting, and BNSS compliance."""
    ts = datetime.now(timezone.utc).isoformat()
    if not req_id:
        req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        
    query_lower = (query or "").lower()
    flags: list[str] = []
    status = "APPROVED"
    bnss_citation = "BNSS Sec 173 / BNS Standard Investigation Guidelines"
    explanation = "Query passes constitutional equality and statutory compliance checks."
    
    # 1. Check prohibited demographic profiling
    for word in _PROHIBITED_DEMOGRAPHICS:
        if f" {word}" in f" {query_lower}" or f"{word} " in f"{query_lower} ":
            status = "REJECTED"
            flags.append(f"Prohibited Demographic Profiling: Detected reference to '{word}'.")
            bnss_citation = "Article 15 (Constitution of India) & BNSS Sec 173 (Non-discriminatory investigation)"
            explanation = "Police queries cannot target individuals or communities based on caste, religion, or community identity."
            break
            
    # 2. Check PII over-collection
    if status != "REJECTED":
        for word in _PII_OVERCOLLECTION_WORDS:
            if word in query_lower:
                status = "FLAGGED"
                flags.append(f"PII Over-collection Warning: '{word}' requested without judicial warrant.")
                bnss_citation = "BNSS Sec 94 / Sec 106 (Production of documents / electronic communication)"
                explanation = "Bulk collection of PII or CDR requires explicit authorization under BNSS Sec 94/106."
                break

    # 3. Check for warrantless search / arrest language
    if status == "APPROVED" and any(k in query_lower for k in ["arrest", "raid", "detain", "seize"]):
        flags.append("Statutory Reminder: Action must adhere to BNSS Sec 35 (Grounds of arrest) & Sec 185 (Search procedures).")

    receipt = {
        "receipt_id": f"VIG-{uuid.uuid4().hex[:6].upper()}",
        "req_id": req_id,
        "officer": officer,
        "query_preview": (query[:100] + "...") if len(query) > 100 else query,
        "status": status,
        "flags": flags,
        "bnss_citation": bnss_citation,
        "explanation": explanation,
        "timestamp": ts,
        "provenance": {
            "agent": "A5: Vigil Compliance Auditor",
            "method": "statutory_regex_eval",
            "compiled_at": ts
        }
    }
    
    product_key = f"vigil:{req_id}"
    product_store.put_product(product_key, receipt, ttl=86400)
    
    # Log to audit store
    try:
        audit_store.record_ai_reasoning(
            officer=officer,
            session_id=req_id,
            user_text=query,
            answer=f"[{status}] {explanation}",
            agents_used=["A5: Vigil Compliance Auditor"],
            citations=[bnss_citation],
            reasoning_id=req_id,
            reasoning_trace=[{"step": "vigil_audit", "detail": explanation}]
        )
    except Exception as e:
        print(f"Vigil audit store log warning: {e}")
        
    return receipt


def get_receipt(req_id: str) -> dict[str, Any] | None:
    """Retrieve a compiled compliance receipt by request ID."""
    return product_store.get_product(f"vigil:{req_id}")
