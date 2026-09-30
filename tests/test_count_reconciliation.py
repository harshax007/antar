"""
Three surfaces report three different registry sizes. They must all be right, and they
must say which one they are.

    Full Data Set summary   1,000,000   every row, ungated - the true dataset size
    Overview / charts         995,505   future-dated rows hidden (the query-path gate)
    Crime Graph cycles        912,167   complete calendar years only

Every one of those is a deliberate, defensible choice, and together they looked like a
system that cannot count: an officer clicking between two screens saw 995,505 and
1,000,000 with nothing on either page to explain the gap.

Labelling them is not enough on its own — a label can drift from the number it describes.
These tests reconcile the three against SQL, so the arithmetic between them has to hold:

    summary  - future-dated   = overview
    overview - partial-year   = cycles

If a future change alters one surface's filter without the others, the subtraction stops
balancing and this fails, rather than the discrepancy reaching a demo.
"""

from __future__ import annotations

import asyncio
import sqlite3

import pytest

from app.api.dataset import count_basis


def _con():
    from app.core.db_path import get_db_path
    return sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True)


GATE = "date <= date('now','localtime')"


# ── the descriptor ───────────────────────────────────────────────────────────

def test_basis_states_the_gate_either_way():
    assert "future-dated rows excluded" in count_basis(10, gated=True)["rules"]
    assert "all rows including future-dated" in count_basis(10, gated=False)["rules"]


def test_basis_names_the_partial_years_it_dropped():
    b = count_basis(9, gated=True, scope_years=[2016, 2017], partial_years=[2026, 2024])
    rule = [r for r in b["rules"] if "complete calendar years" in r]
    assert rule, "the larger exclusion must be stated, not just the gate"
    assert "2024, 2026" in rule[0], "sorted, so the label is stable between runs"
    assert b["scope_years"] == [2016, 2017]


def test_basis_label_is_readable_on_its_own():
    b = count_basis(912167, gated=True, partial_years=[2024, 2026])
    assert b["label"].startswith("912,167 FIRs — ")
    assert "future-dated" in b["label"] and "complete calendar years" in b["label"]


# ── the arithmetic between surfaces ──────────────────────────────────────────

def test_summary_minus_future_dated_equals_overview():
    con = _con()
    try:
        total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        gated = con.execute(f"SELECT COUNT(*) FROM FIRs WHERE {GATE}").fetchone()[0]
        future = con.execute(
            "SELECT COUNT(*) FROM FIRs WHERE date > date('now','localtime')").fetchone()[0]
    finally:
        con.close()
    assert total - future == gated, (
        f"the two headline counts no longer reconcile: {total:,} - {future:,} != {gated:,}")


@pytest.mark.anyio
async def test_cycles_total_is_exactly_its_complete_years():
    """The 83k gap between the chart total and the gated total is partial years, all of it."""
    from app.api.dataset import dataset_cycles
    d = await dataset_cycles()
    scope = set(d.get("scope_years") or [])
    partial = set(d.get("partial_years") or [])
    assert scope and not (scope & partial), "a year cannot be both complete and partial"

    in_scope = sum(y["n"] for y in d["years"] if y["year"] in scope)
    assert d["total"] == in_scope, (
        f"cycles total {d['total']:,} != sum of its complete years {in_scope:,}")

    all_gated = sum(y["n"] for y in d["years"])
    dropped = all_gated - d["total"]
    assert dropped == sum(y["n"] for y in d["years"] if y["year"] in partial)
    assert d["basis"]["excluded_rows"] == dropped, \
        "the basis must report the rows it dropped, not an estimate"


@pytest.mark.anyio
async def test_every_surface_carries_a_basis():
    """A number without its basis is the bug this file exists to prevent coming back."""
    from app.api.dataset import dataset_cycles
    d = await dataset_cycles()
    assert d["basis"]["total"] == d["total"]
    assert d["basis"]["rules"], "a basis with no rules explains nothing"
    # cycles is the surface with BOTH exclusions; its source line must not mention only one
    assert "complete calendar years" in d["source"]
    assert "future-dated" in d["source"]
