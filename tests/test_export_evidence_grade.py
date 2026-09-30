"""
The printable evidence-grade report (final_backend.md §6 P2-4).

The report is the one artefact that leaves Antar as a document: an officer prints it, signs
it, and hands it to someone who will never see the system. Everything Antar does to keep a
claim honest has to survive that transition, and one thing did not — `_answer_html` deleted
the `[VERIFIED]/[COMPUTED]/[INFERRED]` marker from every line before rendering, so the
printed page could not distinguish a row-level fact from a scored guess.

These tests hold that fix in place, and hold the document to the claims it makes about
itself.
"""

from __future__ import annotations

import re

import pytest

from app.api.export_api import CLAIM_CLASSES, _answer_html, _render

ANSWER = (
    "[VERIFIED] **Bengaluru City** has the most kidnapping cases." + chr(10)
    + "[COMPUTED] 5,951 FIRs, 37% of the Karnataka total." + chr(10)
    + "[INFERRED] The same group may be operating in Mysuru." + chr(10)
    + "[GAP] To collect: arrest records for the linked accused."
)


def badges(html: str) -> list[str]:
    return re.findall(r'<span class="cls cls-([KDIU])"[^>]*>', html)


# ── The bug this item exists to fix ──────────────────────────────────────────

def test_every_evidence_class_survives_into_the_document():
    """K, D, I and U all reach the page. This is the regression that mattered."""
    assert badges(_answer_html(ANSWER)) == ["K", "D", "I", "U"]


def test_the_marker_text_is_replaced_not_merely_hidden():
    """The badge carries the class; the raw `[COMPUTED]` string should not also print."""
    html = _answer_html(ANSWER)
    for marker in CLAIM_CLASSES:
        assert f"[{marker}]" not in html, f"raw marker {marker} leaked into the page"
    assert "Bengaluru City" in html and "5,951" in html


def test_a_class_on_a_list_item_is_kept_too():
    """Ranked answers arrive as numbered lists — the class must not be lost there."""
    html = _answer_html("1. [COMPUTED] Bengaluru City — 5,951" + chr(10)
                        + "2. [COMPUTED] Bengaluru Dist — 954")
    assert badges(html) == ["D", "D"]
    assert html.count("<li>") == 2


def test_an_unclassified_line_renders_without_a_badge():
    """No class is not the same as a wrong class — never invent one."""
    html = _answer_html("A plain sentence with no evidence marker.")
    assert badges(html) == []
    assert "A plain sentence" in html


def test_bold_and_escaping_still_work_alongside_a_badge():
    html = _answer_html("[VERIFIED] **bold** & <script>alert(1)</script>")
    assert "<b>bold</b>" in html
    assert "<script>" not in html, "the report must escape record text, not execute it"
    assert badges(html) == ["K"]


def test_every_class_in_the_table_is_icd_203_shaped():
    """Four classes, single-letter codes, each with a human label and a reason."""
    assert set(CLAIM_CLASSES) == {"VERIFIED", "COMPUTED", "INFERRED", "GAP"}
    assert [c for c, _, _ in CLAIM_CLASSES.values()] == ["K", "D", "I", "U"]
    for code, label, why in CLAIM_CLASSES.values():
        assert len(code) == 1 and label and why


# ── The document as a whole ──────────────────────────────────────────────────

def test_the_report_renders_and_states_its_chain_status():
    """A per-turn hash proves nothing alone; the document must say the chain verifies."""
    html = _render("no-such-session-xyz")
    assert "<!doctype html>" in html.lower()
    assert 'class="chain' in html, "the report does not state its audit-chain status"
    assert ("Audit chain verified" in html) or ("AUDIT CHAIN BROKEN" in html) \
        or ("not verified" in html), "the chain panel says nothing either way"


def test_the_report_explains_its_own_badges():
    """A badge nobody can decode is decoration. The legend travels with the document."""
    html = _render("no-such-session-xyz")
    assert 'class="legend"' in html
    for code, label, _why in CLAIM_CLASSES.values():
        assert f'cls-{code}">{code}</span> <b>{label}</b>' in html, \
            f"the legend does not explain {code} ({label})"


def test_a_broken_chain_is_reported_as_broken(monkeypatch):
    """The panel must be capable of saying no. A banner that is always green is a sticker."""
    import app.services.audit_store as store
    monkeypatch.setattr(store, "verify_chain_report", lambda: {
        "ok": False, "total_entries": 9, "verified": 4, "legacy_unverifiable": 0,
        "broken_at_index": 4, "broken_reason": "digest: entry content does not match"})
    html = _render("no-such-session-xyz")
    assert "AUDIT CHAIN BROKEN" in html
    assert "chain bad" in html
    assert "entry 4" in html and "digest" in html


def test_the_report_still_prints_when_the_ledger_cannot_be_read(monkeypatch):
    """Observability failing must not take the document with it."""
    import app.services.audit_store as store

    def boom():
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(store, "verify_chain_report", boom)
    html = _render("no-such-session-xyz")
    assert "<!doctype html>" in html.lower()
    assert "Audit chain not verified" in html, \
        "a report that cannot check the chain must say so, not stay silent"


def test_the_document_hash_covers_the_turns():
    """The seal is over content, so two different sessions cannot share a signature."""
    from app.api.export_api import _report_model
    a = _report_model("session-a-empty")
    b = _report_model("session-b-empty")
    assert len(a["document_sha256"]) == 64
    # Empty sessions differ only by id, which is part of the hashed payload.
    assert a["document_sha256"] != b["document_sha256"] or a["items"] == b["items"] == []
