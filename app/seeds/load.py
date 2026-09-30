"""
Antar — Seed Loader CLI
=================================
Usage (from antar-backend/):

  python -m app.seeds.load                      # generate + validate + write JSON to app/seeds/out/
  python -m app.seeds.load --now 2026-07-22     # world ending at a specific demo date
  python -m app.seeds.load --push --reset       # ALSO wipe + batch-insert into Catalyst Data Store
                                                #   (requires CATALYST_* env vars / catalyst CLI auth)

The generate+validate path is pure-local and deterministic: same SEED + same
--now ⇒ identical world. Validation HARD-FAILS if any planted pattern (P1/P2/P3)
is broken — a failed validation means the demo's WOW moments are not guaranteed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys

# Windows consoles default to cp1252 — force UTF-8 so emoji/Kannada print fine
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from .generator import SEED, build_world
from .planted_patterns import BRAIN_SEED, P1, P2, P3

OUT_DIR = Path(__file__).parent / "out"


# ── Validation — the demo's guarantees, asserted ─────────────────────────────

def validate(world: dict[str, list[dict]], now: date) -> list[str]:
    """Returns a list of failure strings. Empty list = all planted patterns hold."""
    failures: list[str] = []
    crimes = world["crimes"]
    suspects = {s["suspect_id"]: s for s in world["suspects"]}
    rels = world["relationships"]

    # P1 — Yellappa cross-case link
    raju = suspects.get("S0001")
    yella = suspects.get("S0002")
    if not raju or raju["alias"] != "Yellappa":
        failures.append("P1: Raju K. (S0001) missing or alias != 'Yellappa'")
    if not yella or yella["phone_hash"] != (raju or {}).get("phone_hash"):
        failures.append("P1: S0001/S0002 phone_hash not shared")
    anchor = [c for c in crimes if c["fir_number"] == P1["mysuru_anchor_fir"]]
    if len(anchor) != 1:
        failures.append(f"P1: anchor FIR {P1['mysuru_anchor_fir']} count={len(anchor)} (want 1)")
    else:
        age_days = (now - datetime.fromisoformat(anchor[0]["occurred_at"]).date()).days
        if not 200 <= age_days <= 280:
            failures.append(f"P1: anchor case is {age_days} days old (want ~240 ≈ 8 months)")
    contacts_of = lambda sid: {r["suspect_b"] for r in rels if r["suspect_a"] == sid} | \
                              {r["suspect_a"] for r in rels if r["suspect_b"] == sid}
    common = contacts_of("S0001") & contacts_of("S0002")
    if len(common & set(P1["common_contacts"])) < 3:
        failures.append(f"P1: common contacts {common} — need the 3 planted ones")

    # P2 — Rajajinagar spike, z in band
    demo_start = now - timedelta(days=6)
    weekly: Counter = Counter()
    demo_count = 0
    for c in crimes:
        if c["crime_type"] == P2["crime_type"] and c["zone"] == P2["zone"]:
            d = datetime.fromisoformat(c["occurred_at"]).date()
            if d >= demo_start:
                demo_count += 1
            else:
                weeks_back = ((demo_start - d).days // 7) + 1
                if weeks_back <= len(P2["trailing_weekly_counts"]):
                    weekly[weeks_back] += 1
    series = [weekly.get(k, 0) for k in range(len(P2["trailing_weekly_counts"]), 0, -1)]
    mu = statistics.mean(series)
    sigma = statistics.pstdev(series)
    z = (demo_count - mu) / sigma if sigma else 0.0
    if demo_count != P2["demo_week_count"]:
        failures.append(f"P2: demo-week count={demo_count} (want {P2['demo_week_count']})")
    if not 1.8 <= mu <= 2.8:
        failures.append(f"P2: trailing μ={mu:.2f} outside [1.8, 2.8] — series {series}")
    lo, hi = P2["expected_z_range"]
    if not lo <= z <= hi:
        failures.append(f"P2: z={z:.2f} outside [{lo}, {hi}] (μ={mu:.2f}, σ={sigma:.2f})")

    # P3 — evening theft concentration in hot zones
    def evening_share(zone_filter):
        thefts = [c for c in crimes if c["crime_type"] == "theft" and zone_filter(c["zone"])]
        if not thefts:
            return 0.0, 0
        ev = sum(1 for c in thefts
                 if datetime.fromisoformat(c["occurred_at"]).hour in P3["evening_hours"])
        return ev / len(thefts), len(thefts)

    hot_share, hot_n = evening_share(lambda z_: z_ in P3["hot_zones"])
    cold_share, _ = evening_share(lambda z_: z_ not in P3["hot_zones"])
    if hot_share < 0.55:
        failures.append(f"P3: hot-zone evening share {hot_share:.0%} < 55%")
    if hot_share - cold_share < 0.15:
        failures.append(f"P3: hot/cold contrast too weak ({hot_share:.0%} vs {cold_share:.0%})")
    if hot_n < 150:
        failures.append(f"P3: only {hot_n} thefts in hot zones — heatmap will look thin")

    # Volume sanity
    expected_min = {"crimes": 5000, "suspects": 300, "stations": 60,
                    "relationships": 600, "crime_suspects": 2500, "victims": 800,
                    "property": 1500}
    for table, n in expected_min.items():
        if len(world[table]) < n:
            failures.append(f"volume: {table} has {len(world[table])} rows (want ≥ {n})")
    firs = [c["fir_number"] for c in crimes]
    if len(firs) != len(set(firs)):
        failures.append("crimes: duplicate fir_number values")

    return failures, {"p2_mu": round(mu, 2), "p2_sigma": round(sigma, 2), "p2_z": round(z, 2),
                      "p2_series": series, "p2_demo_count": demo_count,
                      "p3_hot_evening": round(hot_share, 2), "p3_cold_evening": round(cold_share, 2)}


# ── Push to Catalyst Data Store (zcatalyst-sdk) ──────────────────────────────

PUSH_ORDER = ["stations", "officers", "suspects", "victims", "crimes",
              "crime_suspects", "relationships", "financial_links", "property"]
CHUNK = 100  # [VERIFY: Data Store bulk-insert row limit per call on free tier]


def push_to_datastore(world: dict[str, list[dict]], reset: bool) -> None:
    """
    Batch-insert into Catalyst Data Store using the real zcatalyst-sdk API:
        app.datastore().table(name).insert_rows(List[Dict])   ← bulk insert (VERIFIED)
        app.datastore().table(name).get_paged_rows() + delete_rows(ids)  ← reset
    Standalone admin init goes through app.core.catalyst.get_app() (see [VERIFY]s there).

    Requires .env admin credentials. Run: python -m app.seeds.load --push --reset
    """
    import time
    from app.core.catalyst import get_app

    app = get_app()                      # standalone admin context (no request)
    datastore = app.datastore()

    for table_name in PUSH_ORDER:
        table = datastore.table(table_name)
        rows = world[table_name]

        if reset:
            _truncate_table(table, table_name)

        inserted = 0
        for i in range(0, len(rows), CHUNK):
            table.insert_rows(rows[i:i + CHUNK])     # bulk insert (max ~CHUNK per call)
            inserted += len(rows[i:i + CHUNK])
            time.sleep(0.4)                          # rate-limit courtesy [VERIFY actual limit]
        print(f"  ✓ pushed {inserted:>5} rows → {table_name}")


def _truncate_table(table, table_name: str) -> None:
    """
    Delete all rows from a table (paged read → delete_rows by id).
    [VERIFY] whether Data Store offers a native truncate; if so, prefer it.
    The ROWID column name is [VERIFY] — Catalyst typically exposes 'ROWID'.
    """
    removed = 0
    try:
        while True:
            page = table.get_paged_rows(max_rows=200)
            items = getattr(page, "data", None) or page  # [VERIFY] page shape (.data vs list)
            if not items:
                break
            ids = [row.get("ROWID") or row.get("row_id") for row in items]  # [VERIFY] id key
            ids = [i for i in ids if i]
            if not ids:
                break
            table.delete_rows(ids)
            removed += len(ids)
        print(f"  · reset '{table_name}' — removed {removed} existing rows")
    except Exception as e:
        print(f"  ! reset of '{table_name}' failed ({e}) — truncate via console if needed")


def spot_check() -> None:
    """
    Phase 1, Step 1.7 validation: 5 ZCQL spot-queries (incl. one OLAP aggregation)
    confirming the planted patterns survived the round-trip into Data Store.
    """
    from app.core.catalyst import zcql_query
    checks = [
        ("P1 anchor FIR present",
         f"SELECT fir_number FROM crimes WHERE fir_number = '{P1['mysuru_anchor_fir']}'", False),
        ("P1 Raju K. alias",
         "SELECT full_name, alias FROM suspects WHERE suspect_id = 'S0001'", False),
        ("Total crimes",
         "SELECT COUNT(crime_id) AS n FROM crimes", True),
        ("P2 Rajajinagar chain-snatching count",
         "SELECT COUNT(crime_id) AS n FROM crimes WHERE zone = 'Rajajinagar' "
         "AND crime_type = 'chain_snatching'", True),
        ("P3 theft by zone (OLAP)",
         "SELECT zone, COUNT(crime_id) AS n FROM crimes WHERE crime_type = 'theft' "
         "GROUP BY zone ORDER BY n DESC", True),
    ]
    print("\n🔎 ZCQL spot-checks against Data Store:")
    for label, q, olap in checks:
        try:
            rows = zcql_query(q, olap=olap)
            print(f"   ✓ {label}: {rows[:3]}")
        except Exception as e:
            print(f"   ✗ {label}: {e}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Antar synthetic world loader")
    ap.add_argument("--now", type=date.fromisoformat, default=date.today(),
                    help="world end date / demo date (YYYY-MM-DD, default today)")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="JSON output directory")
    ap.add_argument("--push", action="store_true", help="push to Catalyst Data Store")
    ap.add_argument("--reset", action="store_true", help="wipe tables before push")
    args = ap.parse_args()

    print(f"🌱 Generating world  (SEED={SEED}, now={args.now}) …")
    world = build_world(args.now)

    failures, stats = validate(world, args.now)
    print("\n📊 World summary")
    for t in ["stations", "officers", "suspects", "victims", "crimes",
              "crime_suspects", "relationships", "financial_links", "property"]:
        print(f"   {t:<16} {len(world[t]):>6} rows")
    print(f"\n🎯 Planted-pattern check")
    print(f"   P2 trailing weekly: {stats['p2_series']}")
    print(f"   P2 μ={stats['p2_mu']}  σ={stats['p2_sigma']}  demo-week={stats['p2_demo_count']}"
          f"  →  z = {stats['p2_z']}")
    print(f"   P3 evening share: hot zones {stats['p3_hot_evening']:.0%}"
          f" vs elsewhere {stats['p3_cold_evening']:.0%}")

    if failures:
        print("\n❌ VALIDATION FAILED — demo guarantees broken:")
        for f in failures:
            print(f"   ✗ {f}")
        sys.exit(1)
    print("\n✅ All planted patterns hold (P1 Yellappa link · P2 z-spike · P3 clusters)")

    args.out.mkdir(parents=True, exist_ok=True)
    for table, rows in world.items():
        (args.out / f"{table}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.out / "brain_seed.json").write_text(
        json.dumps(BRAIN_SEED, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.out / "_summary.json").write_text(json.dumps({
        "seed": SEED, "now": args.now.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "rows": {t: len(r) for t, r in world.items()}, "pattern_stats": stats,
    }, indent=2), encoding="utf-8")
    print(f"💾 JSON written → {args.out}")

    if args.push:
        print("\n☁️  Pushing to Catalyst Data Store …")
        push_to_datastore(world, args.reset)
        spot_check()
        print("\n✅ Push complete.")


if __name__ == "__main__":
    main()
