"""
Antar — Synthetic World Generator
===========================================
Builds the full demo world per Strategy v4.0 §4.5:
  ~5,000 crimes · 300 suspects · 60 stations · Jan 2024 → now
  with planted patterns P1 (Yellappa cross-case), P2 (Rajajinagar z≈3.1 spike),
  P3 (evening theft clusters + festival bump) woven in deterministically.

Pure Python (no numpy) so it runs anywhere. Deterministic: same SEED + same
--now date ⇒ byte-identical world. SEED gets LOCKED on Jul 11 — after that,
never change it.

Entry point: python -m app.seeds.load  (see load.py for the CLI)
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from .planted_patterns import P1, P2, P3, DEMO_OFFICERS

SEED = 20260726  # ← LOCKED on Jul 11 (submission date as constant). Do not touch after.

WORLD_START = date(2024, 1, 1)

# ── Reference data (M2's data_reference.md feeds refinements later) ──────────

BLR_ZONES = [
    # (zone, code, base_lat, base_lon)
    ("Rajajinagar",     "RJN", 12.9866, 77.5517),
    ("Gandhinagar",     "GNR", 12.9774, 77.5765),
    ("Jayanagar",       "JYN", 12.9308, 77.5838),
    ("Malleshwaram",    "MLW", 13.0035, 77.5709),
    ("Indiranagar",     "IND", 12.9719, 77.6412),
    ("Whitefield",      "WHF", 12.9698, 77.7500),
    ("Yeshwanthpur",    "YPR", 13.0280, 77.5400),
    ("Banashankari",    "BSK", 12.9255, 77.5468),
    ("KR Puram",        "KRP", 13.0070, 77.6950),
    ("Hebbal",          "HBL", 13.0358, 77.5970),
]
DISTRICT_STATIONS = [
    # (zone, code_prefix, n_stations, base_lat, base_lon, district, range_name, unit_type)
    # [VERIFY] exact KSP Range / Commissionerate structure with SCRB.
    ("Mysuru-Devaraja", "MYS", 4, 12.3052, 76.6552, "Mysuru", "Mysuru City", "Commissionerate"),
    ("Mysuru-Nazarbad", "MYN", 2, 12.2958, 76.6602, "Mysuru", "Mysuru City", "Commissionerate"),
    ("Hubballi",        "HBI", 4, 15.3647, 75.1240, "Dharwad", "Northern Range", "District Police"),
    ("Belagavi",        "BGV", 4, 15.8497, 74.4977, "Belagavi", "Northern Range", "District Police"),
    ("Mangaluru",       "MNG", 3, 12.9141, 74.8560, "Dakshina Kannada", "Western Range", "District Police"),
    ("Kalaburagi",      "KLB", 3, 17.3297, 76.8343, "Kalaburagi", "Kalaburagi Range", "District Police"),
]

# CCTNS-aligned crime catalogue:
#   (crime_type, weight, ipc_section, bns_section, act_class, severity_range)
# The Bharatiya Nyaya Sanhita (BNS) 2023 replaced the IPC for offences registered from
# 2024-07-01. CCTNS records carry the Act + Sections; our data reflects the transition
# (IPC before that date, BNS after). Special & Local Laws (SLL: NDPS, IT Act) are unchanged.
# [VERIFY] exact BNS section numbers with the KSP legal cell — the equivalents below are the
# widely-cited mappings (theft→303, snatching→304 (new offence), robbery→309, cheating→318,
# murder→103, kidnapping→137, rioting→191, hurt→115/118, cruelty→85/86).
CRIME_TYPES = [
    ("theft",            0.26, "IPC 379",     "BNS 303(2)",          "general", (1, 3)),
    ("assault",          0.13, "IPC 323/324", "BNS 115(2)/118",      "general", (2, 4)),
    ("burglary",         0.11, "IPC 457/380", "BNS 331(4)/305",      "general", (2, 4)),
    ("cheating_fraud",   0.10, "IPC 420",     "BNS 318(4)",          "general", (2, 3)),
    ("chain_snatching",  0.00, "IPC 356/379", "BNS 304(2)",          "general", (2, 4)),
    ("robbery",          0.07, "IPC 392",     "BNS 309(4)",          "general", (3, 5)),
    ("vehicle_theft",    0.09, "IPC 379",     "BNS 303(2)",          "general", (1, 3)),
    ("ndps",             0.05, "NDPS Act 1985 s.20", "NDPS Act 1985 s.20", "SLL", (3, 5)),
    ("domestic_violence",0.06, "IPC 498A",    "BNS 85/86",           "general", (2, 4)),
    ("cybercrime",       0.06, "IT Act s.66", "IT Act s.66 r/w BNS 318", "SLL", (2, 3)),
    ("rioting",          0.03, "IPC 147",     "BNS 191(2)",          "general", (3, 5)),
    ("murder",           0.02, "IPC 302",     "BNS 103(1)",          "general", (5, 5)),
    ("kidnapping",       0.02, "IPC 363",     "BNS 137(2)",          "general", (4, 5)),
]
IPC_BY_TYPE = {t: ipc for t, _, ipc, _, _, _ in CRIME_TYPES}
BNS_BY_TYPE = {t: bns for t, _, _, bns, _, _ in CRIME_TYPES}
ACT_CLASS_BY_TYPE = {t: ac for t, _, _, _, ac, _ in CRIME_TYPES}
SEV_BY_TYPE = {t: sev for t, _, _, _, _, sev in CRIME_TYPES}
BNS_EFFECTIVE = date(2024, 7, 1)


def acts_and_sections(ctype: str, occurred: date) -> tuple[str, str]:
    """CCTNS Act + Sections: IPC before 2024-07-01, BNS after; SLL (special laws) unchanged."""
    if ACT_CLASS_BY_TYPE[ctype] == "SLL":
        return "SLL", IPC_BY_TYPE[ctype]
    if occurred < BNS_EFFECTIVE:
        return "IPC", IPC_BY_TYPE[ctype]
    return "BNS", BNS_BY_TYPE[ctype]


# CCTNS Property module — stolen/recovered property per crime type
PROPERTY_BY_TYPE = {
    "theft":           ["Mobile phone", "Cash", "Laptop", "Gold ornaments", "Bicycle"],
    "chain_snatching": ["Gold chain", "Gold mangalsutra", "Gold ornaments"],
    "robbery":         ["Cash", "Mobile phone", "Gold ornaments", "Wristwatch"],
    "burglary":        ["Gold ornaments", "Cash", "Electronics", "Silver articles"],
    "vehicle_theft":   ["Two-wheeler (motorcycle)", "Car", "Auto-rickshaw", "Scooter"],
}
PROPERTY_VALUE_RANGE = {  # INR
    "theft": (2000, 80000), "chain_snatching": (15000, 120000), "robbery": (5000, 150000),
    "burglary": (20000, 500000), "vehicle_theft": (40000, 900000),
}
ARREST_STATUSES = ["arrested", "released_on_bail", "absconding", "not_arrested"]
CASE_STATUSES = ["under_investigation", "charge_sheeted", "disposed"]  # CCTNS FIR stages

FIRST_M = ["Ravi", "Suresh", "Manju", "Prakash", "Naveen", "Kiran", "Mahesh", "Santosh",
           "Lokesh", "Harish", "Girish", "Umesh", "Venkatesh", "Shivu", "Raghav",
           "Anand", "Basavaraj", "Chandru", "Dinesh", "Eshwar", "Ganesh", "Hanumantha",
           "Jagadish", "Krishna", "Lakshman", "Madhu", "Nagaraj", "Puneeth", "Ramesh", "Somu"]
FIRST_F = ["Lakshmi", "Sowmya", "Asha", "Geetha", "Manjula", "Rekha", "Savitha", "Shobha",
           "Padma", "Roopa", "Kavitha", "Vani", "Bhagya", "Nagamma", "Yashoda"]
SURNAMES = ["Gowda", "Reddy", "Shetty", "Hegde", "Kumar", "Naik", "Rao", "Patil",
            "Achar", "Bhat", "Poojary", "Swamy", "Murthy", "Setty", "Kambar", "M.", "K.", "S."]
OCCUPATIONS = ["driver", "daily wage", "mechanic", "vendor", "unemployed", "painter",
               "electrician", "delivery rider", "lorry cleaner", "scrap dealer",
               "construction worker", "garage helper", "security guard", "unknown"]
VICTIM_OCCUPATIONS = ["teacher", "shop owner", "homemaker", "student", "engineer",
                      "retired", "nurse", "clerk", "vendor", "driver", "tailor"]
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
REL_TYPES = ["associate", "family", "co_accused", "shared_phone", "shared_vehicle"]


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def build_world(now: date) -> dict[str, list[dict]]:
    """Generate every table deterministically. Returns {table_name: rows}."""
    rng = random.Random(SEED)
    world: dict[str, list[dict]] = {}

    # ── stations (60) ─────────────────────────────────────────────────────────
    stations = []
    for zone, code, lat, lon in BLR_ZONES:
        for i in range(1, 5):  # 4 per zone = 40 Bengaluru stations
            stations.append({
                "station_code": f"BLR-{code}-{i:02d}",
                "name": f"{zone} PS-{i}" if i > 1 else f"{zone} PS",
                "district": "Bengaluru City",
                "zone": zone,
                # CCTNS jurisdiction hierarchy: Commissionerate → Range → Sub-Division → PS
                "unit_type": "Commissionerate",
                "range_name": "Bengaluru City",
                "sub_division": f"{zone} Sub-Division",
                "lat": round(lat + rng.uniform(-0.015, 0.015), 6),
                "lon": round(lon + rng.uniform(-0.015, 0.015), 6),
            })
    for zone, code, n, lat, lon, district, range_name, unit_type in DISTRICT_STATIONS:
        for i in range(1, n + 1):
            stations.append({
                "station_code": f"{code}-{i:02d}",
                "name": f"{zone} PS-{i}" if i > 1 else f"{zone} PS",
                "district": district,
                "zone": zone,
                "unit_type": unit_type,
                "range_name": range_name,
                "sub_division": f"{zone} Sub-Division",
                "lat": round(lat + rng.uniform(-0.02, 0.02), 6),
                "lon": round(lon + rng.uniform(-0.02, 0.02), 6),
            })
    stations.append({"station_code": "SCRB-HQ", "name": "SCRB Headquarters",
                     "district": "Bengaluru City", "zone": "Gandhinagar",
                     "unit_type": "State HQ", "range_name": "SCRB", "sub_division": "SCRB",
                     "lat": 12.9784, "lon": 77.5917})
    world["stations"] = stations
    stations_by_zone: dict[str, list[dict]] = {}
    for s in stations:
        stations_by_zone.setdefault(s["zone"], []).append(s)

    # ── suspects (300; S0001/S0002 are P1's pair) ─────────────────────────────
    suspects = [dict(P1["bengaluru_suspect"]), dict(P1["mysuru_suspect"])]
    all_zones = [z for z, *_ in BLR_ZONES] + [z for z, *_ in DISTRICT_STATIONS]
    for i in range(3, 301):
        sid = f"S{i:04d}"
        gender = "M" if rng.random() < 0.85 else "F"
        first = rng.choice(FIRST_M if gender == "M" else FIRST_F)
        is_repeat = i <= 60  # S0003–S0060: repeat offenders
        priors = rng.randint(2, 9) if is_repeat else rng.randint(0, 2)
        suspects.append({
            "suspect_id": sid,
            "full_name": f"{first} {rng.choice(SURNAMES)}",
            "father_name": f"{rng.choice(FIRST_M)} {rng.choice(SURNAMES)}",  # CCTNS: s/o
            "alias": (rng.choice(["Chikka", "Dodda", "Kulla", "Bullet", "Auto", "Tiger",
                                  "Silent", "Gym"]) + " " + first) if rng.random() < 0.25 else "",
            "age": rng.randint(19, 55),
            "gender": gender,
            "nationality": "Indian",
            "phone_hash": f"PH-{rng.getrandbits(24):06x}",
            "address_zone": rng.choice(all_zones),
            "occupation": rng.choice(OCCUPATIONS),
            "prior_count": priors,
            # CCTNS arrest status (repeat offenders likelier arrested/bailed)
            "arrest_status": rng.choices(
                ARREST_STATUSES, [0.35, 0.30, 0.10, 0.25] if is_repeat else [0.20, 0.20, 0.05, 0.55])[0],
        })
    # P1 accused: enrich the planted pair with CCTNS fields matching their brain summaries
    P1_ACCUSED = {
        "S0001": {"father_name": "Krishnappa Gowda", "nationality": "Indian", "arrest_status": "released_on_bail"},
        "S0002": {"father_name": "Mahadeva M.", "nationality": "Indian", "arrest_status": "absconding"},
    }
    for s in suspects:
        s.setdefault("father_name", P1_ACCUSED.get(s["suspect_id"], {}).get("father_name", ""))
        for k, v in P1_ACCUSED.get(s["suspect_id"], {}).items():
            s[k] = v
        s.setdefault("nationality", "Indian")
        s.setdefault("arrest_status", "not_arrested")
    world["suspects"] = suspects
    # P1's common contacts live in Bengaluru-West-ish zones for realism
    for sid in P1["common_contacts"]:
        srow = next(s for s in suspects if s["suspect_id"] == sid)
        srow["address_zone"] = "Rajajinagar"

    # ── officers ──────────────────────────────────────────────────────────────
    officers = [dict(o) for o in DEMO_OFFICERS]
    IO_RANKS = ["Police Sub-Inspector (PSI)", "Sub-Inspector (SI)", "Police Inspector (PI)"]
    OTHER_RANKS = ["Head Constable (HC)", "Police Constable (PC)", "Assistant Sub-Inspector (ASI)"]
    of_seq = 2001
    for st in stations:  # 2 officers/station: an investigating-rank + a support rank
        for rank in (rng.choice(IO_RANKS), rng.choice(OTHER_RANKS)):
            officers.append({
                "officer_id": f"OF-{of_seq}",
                "name": f"{rng.choice(FIRST_M + FIRST_F)} {rng.choice(SURNAMES)}",
                "rank": rank,
                "station_code": st["station_code"],
                "role_name": "Constable",
            })
            of_seq += 1
    world["officers"] = officers
    officers_by_station: dict[str, list[dict]] = {}
    for o in officers:
        officers_by_station.setdefault(o.get("station_code", ""), []).append(o)

    def pick_io(station_code: str) -> dict:
        pool = officers_by_station.get(station_code) or officers
        ios = [o for o in pool if "Inspector" in o.get("rank", "")]
        o = rng.choice(ios or pool)
        return {"io_officer_id": o["officer_id"], "io_name": o["name"], "io_rank": o["rank"]}

    # ── crimes ────────────────────────────────────────────────────────────────
    crimes: list[dict] = []
    fir_seq: dict[tuple[int, str], int] = {}
    reserved_fir = P1["mysuru_anchor_fir"]

    def city_code(station_code: str) -> str:
        return "MYS" if station_code.startswith(("MYS", "MYN")) else station_code.split("-")[0]

    def next_fir(year: int, city: str) -> str:
        key = (year, city)
        while True:
            fir_seq[key] = fir_seq.get(key, 0) + 1
            fir = f"{year}-{city}-{fir_seq[key]:04d}"
            if fir != reserved_fir:
                return fir

    def add_crime(crime_type: str, zone: str, occurred: datetime, *,
                  fir: str | None = None, status: str | None = None) -> dict:
        st = rng.choice(stations_by_zone[zone])
        year = occurred.year
        sev_lo, sev_hi = SEV_BY_TYPE[crime_type]
        act, sections = acts_and_sections(crime_type, occurred.date())
        io = pick_io(st["station_code"])
        complainant = f"{rng.choice(FIRST_M + FIRST_F)} {rng.choice(SURNAMES)}"
        row = {
            "crime_id": f"C{len(crimes) + 1:05d}",
            "fir_number": fir or next_fir(year, city_code(st["station_code"])),
            "crime_type": crime_type,
            "act": act,                          # IPC | BNS | SLL  (CCTNS)
            "acts_sections": sections,           # e.g. "BNS 303(2)"  (CCTNS Acts & Sections)
            "cognizable": True,                  # all seeded types are cognizable offences
            "station_code": st["station_code"],
            "district": st["district"],
            "zone": zone,
            "lat": round(st["lat"] + rng.uniform(-0.008, 0.008), 6),
            "lon": round(st["lon"] + rng.uniform(-0.008, 0.008), 6),
            "occurred_at": occurred.isoformat(sep=" ", timespec="minutes"),
            "reported_at": (occurred + timedelta(hours=rng.uniform(1, 36))).isoformat(sep=" ", timespec="minutes"),
            "status": status or rng.choices(CASE_STATUSES, [0.45, 0.30, 0.25])[0],
            "severity": rng.randint(sev_lo, sev_hi),
            "complainant_name": complainant,
            "io_officer_id": io["io_officer_id"],
            "io_name": io["io_name"],
            "io_rank": io["io_rank"],
            "narrative_doc_id": "",
        }
        row["narrative_doc_id"] = f"DOC-{row['fir_number']}"
        crimes.append(row)
        return row

    def rand_time(d: date, evening_p: float, evening_hours: list[int]) -> datetime:
        if rng.random() < evening_p:
            h = rng.choice(evening_hours)
        else:
            h = rng.randint(6, 17)
        return datetime(d.year, d.month, d.day, h, rng.randint(0, 59))

    total_days = (now - WORLD_START).days

    def rand_date(start: date = WORLD_START, end: date | None = None) -> date:
        end = end or now
        return start + timedelta(days=rng.randint(0, max((end - start).days, 1)))

    # P2a — controlled Rajajinagar chain-snatching series ----------------------
    demo_week_start = now - timedelta(days=6)              # 7-day window ending today
    trailing = P2["trailing_weekly_counts"]
    p2_rows: list[dict] = []
    for wi, count in enumerate(trailing):                  # oldest → newest
        wk_start = demo_week_start - timedelta(weeks=len(trailing) - wi)
        for _ in range(count):
            d = wk_start + timedelta(days=rng.randint(0, 6))
            p2_rows.append(add_crime("chain_snatching", P2["zone"],
                                     rand_time(d, 0.85, P2["evening_bias_hours"])))
    for _ in range(P2["demo_week_count"]):                 # the spike: exactly 8
        d = demo_week_start + timedelta(days=rng.randint(0, 6))
        p2_rows.append(add_crime("chain_snatching", P2["zone"],
                                 rand_time(d, 0.85, P2["evening_bias_hours"]),
                                 status="under_investigation"))
    # Jan-2025 gang surge (grounds the resolved_pattern brain row)
    surge_start = date(2025, 1, 6)
    for wi, count in enumerate(P2["jan2025_surge_weekly"]):
        wk = surge_start + timedelta(weeks=wi)
        for _ in range(count):
            d = wk + timedelta(days=rng.randint(0, 6))
            add_crime("chain_snatching", P2["zone"],
                      rand_time(d, 0.85, P2["evening_bias_hours"]), status="disposed")
    # historical pre-window trickle (Jan 2024 → window start), avg ~2.2/wk
    pre_window_end = demo_week_start - timedelta(weeks=len(trailing))
    wk = _week_start(WORLD_START)
    while wk < pre_window_end:
        if not (date(2025, 1, 6) <= wk <= date(2025, 1, 26)):  # don't double the surge
            for _ in range(rng.choices([0, 1, 2, 3, 4], [0.10, 0.25, 0.35, 0.20, 0.10])[0]):
                d = wk + timedelta(days=rng.randint(0, 6))
                if d < pre_window_end:
                    add_crime("chain_snatching", P2["zone"],
                              rand_time(d, 0.85, P2["evening_bias_hours"]))
        wk += timedelta(weeks=1)
    # light chain-snatching elsewhere (other zones, low rate — keeps realism)
    for zone in [z for z, *_ in BLR_ZONES if z != P2["zone"]]:
        for _ in range(rng.randint(8, 20)):
            add_crime("chain_snatching", zone,
                      rand_time(rand_date(), 0.7, P2["evening_bias_hours"]))

    # P1 — Mysuru cluster (~8 months ago) + Raju K.'s Bengaluru record ---------
    mys_anchor_day = now - timedelta(days=30 * P1["mysuru_case_months_ago"])
    p1_mys_crimes = []
    for i in range(P1["mysuru_cluster_size"]):
        # anchor case (i==0, FIR ...0089) is the EARLIEST in the cluster, so retrieval
        # (which picks the earliest crime) surfaces it as the cross-case anchor.
        d = mys_anchor_day if i == 0 else mys_anchor_day + timedelta(days=rng.randint(1, 12))
        row = add_crime("burglary", "Mysuru-Devaraja",
                        rand_time(d, 0.9, [22, 23]),
                        fir=P1["mysuru_anchor_fir"] if i == 0 else None,
                        status="under_investigation")
        p1_mys_crimes.append(row)
    p1_blr_crimes = []
    for months_ago, ctype in [(6, "robbery"), (4, "robbery"), (2, "theft"), (1, "robbery")]:
        d = now - timedelta(days=30 * months_ago + rng.randint(0, 10))
        p1_blr_crimes.append(add_crime(ctype, "Rajajinagar",
                                       rand_time(d, 0.8, [18, 19, 20]), status="under_investigation"))

    # Background crimes to ~5,000 total -----------------------------------------
    bg_types = [(t, w) for t, w, *_ in CRIME_TYPES if w > 0]
    bg_names = [t for t, _ in bg_types]
    bg_weights = [w for _, w in bg_types]
    blr_zone_names = [z for z, *_ in BLR_ZONES]
    district_zone_names = [z for z, *_ in DISTRICT_STATIONS]
    festival_start = date.fromisoformat(P3["festival_week_start"])
    festival_end = festival_start + timedelta(days=7)

    while len(crimes) < 5000:
        ctype = rng.choices(bg_names, bg_weights)[0]
        # P3: ~40% of THEFT is concentrated in the 2 hot zones (so they're visibly the top
        # hotspots on the map/T11). Other crime: 75% Bengaluru, 25% districts.
        if ctype == "theft" and rng.random() < 0.40:
            zone = rng.choice(P3["hot_zones"])
        else:
            zone = rng.choice(blr_zone_names) if rng.random() < 0.75 else rng.choice(district_zone_names)
        d = rand_date()
        if ctype == "theft":
            in_hot = zone in P3["hot_zones"]
            # festival bump: extra prob mass lands in festival week for hot zones
            if in_hot and rng.random() < 0.06:
                d = festival_start + timedelta(days=rng.randint(0, 6))
            evening_p = P3["evening_share_in_hot_zones"] if in_hot else P3["evening_share_elsewhere"]
            occurred = rand_time(d, evening_p, P3["evening_hours"])
        else:
            occurred = rand_time(d, 0.45, [18, 19, 20, 21])
        add_crime(ctype, zone, occurred)

    world["crimes"] = crimes

    # ── property (CCTNS Property module: stolen / recovered) ───────────────────
    property_rows: list[dict] = []
    pid = 0
    for c in crimes:
        kinds = PROPERTY_BY_TYPE.get(c["crime_type"])
        if not kinds:
            continue
        lo, hi = PROPERTY_VALUE_RANGE[c["crime_type"]]
        n_items = rng.choices([1, 2], [0.8, 0.2])[0]
        for _ in range(n_items):
            pid += 1
            status = rng.choices(["stolen", "recovered", "partially_recovered"],
                                 [0.62, 0.28, 0.10])[0]
            property_rows.append({
                "property_id": f"P{pid:05d}",
                "crime_id": c["crime_id"],
                "fir_number": c["fir_number"],
                "property_type": rng.choice(kinds),
                "value_inr": rng.randint(lo, hi),
                "status": status,
            })
    world["property"] = property_rows

    # ── victims (~800, privacy-shaped) ────────────────────────────────────────
    world["victims"] = [{
        "victim_id": f"V{i:04d}",
        "age_band": rng.choice(AGE_BANDS),
        "gender": rng.choice(["M", "F", "F"]),  # snatching/theft skew female victims
        "occupation": rng.choice(VICTIM_OCCUPATIONS),
        "zone": rng.choice(all_zones),
    } for i in range(1, 801)]

    # ── crime_suspects (P1 wiring first, then background) ─────────────────────
    crime_suspects: list[dict] = []
    cs_id = 0

    def link(crime_id: str, suspect_id: str, role: str = "accused"):
        nonlocal cs_id
        cs_id += 1
        crime_suspects.append({"id": f"CS{cs_id:05d}", "crime_id": crime_id,
                               "suspect_id": suspect_id, "role": role})

    for row in p1_mys_crimes:
        link(row["crime_id"], "S0002")                       # Yellappa on Mysuru cluster
    link(p1_mys_crimes[0]["crime_id"], "S0003", "abettor")    # contact in anchor case
    for row in p1_blr_crimes:
        link(row["crime_id"], "S0001")                       # Raju K.'s Bengaluru record
    link(p1_blr_crimes[0]["crime_id"], "S0004", "abettor")

    repeat_ids = [f"S{i:04d}" for i in range(3, 61)]
    other_ids = [f"S{i:04d}" for i in range(61, 301)]
    p1_crime_ids = {r["crime_id"] for r in p1_mys_crimes + p1_blr_crimes}
    for c in crimes:
        if c["crime_id"] in p1_crime_ids:
            continue
        r = rng.random()
        n = 0 if r < 0.45 else 1 if r < 0.85 else 2 if r < 0.97 else 3
        if n:
            pool = repeat_ids if rng.random() < 0.5 else other_ids
            for sid in rng.sample(pool, n):
                link(c["crime_id"], sid, "accused" if rng.random() < 0.85 else "abettor")
    world["crime_suspects"] = crime_suspects

    # ── relationships (P1 edges first — the 3 common contacts) ────────────────
    relationships: list[dict] = []
    rel_id = 0

    def rel(a: str, b: str, rtype: str, strength: int, source: str = ""):
        nonlocal rel_id
        rel_id += 1
        relationships.append({"rel_id": f"R{rel_id:05d}", "suspect_a": a, "suspect_b": b,
                              "rel_type": rtype, "strength": strength,
                              "source_crime_id": source})

    anchor_id = p1_mys_crimes[0]["crime_id"]
    for contact in P1["common_contacts"]:
        rel("S0001", contact, "associate", 3, p1_blr_crimes[0]["crime_id"])
        rel("S0002", contact, "associate", 2, anchor_id)
    rel("S0001", "S0002", "shared_phone", 3, "")             # the silent thread
    # co_accused edges derived from shared crimes (capped)
    by_crime: dict[str, list[str]] = {}
    for cs in crime_suspects:
        by_crime.setdefault(cs["crime_id"], []).append(cs["suspect_id"])
    seen_pairs = set()
    for cid, sids in by_crime.items():
        if len(sids) >= 2:
            for i in range(len(sids)):
                for j in range(i + 1, len(sids)):
                    pair = tuple(sorted((sids[i], sids[j])))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        rel(pair[0], pair[1], "co_accused", rng.randint(2, 3), cid)
    # random social edges to ~650 total
    sus_ids = [s["suspect_id"] for s in suspects]
    while len(relationships) < 650:
        a, b = rng.sample(sus_ids, 2)
        pair = tuple(sorted((a, b)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        rel(a, b, rng.choices(REL_TYPES, [0.45, 0.20, 0.0, 0.20, 0.15])[0],
            rng.randint(1, 2), "")
    world["relationships"] = relationships

    # ── financial_links (M7 schema-level) ─────────────────────────────────────
    world["financial_links"] = [{
        "link_id": f"FL{i:04d}",
        "suspect_id": rng.choice(repeat_ids + ["S0001", "S0002"]),
        "counterparty": f"ACC-{rng.getrandbits(20):05x}",
        "txn_count": rng.randint(2, 40),
        "amount_band": rng.choice(["<10k", "10k-50k", "50k-2L", "2L-10L"]),
        "flag_reason": rng.choice(["rapid_cash_out", "structuring", "mule_pattern",
                                   "known_receiver", "hawala_suspect"]),
    } for i in range(1, 81)]

    world["alerts"] = []      # created by the Forecast Agent, never seeded
    world["audit_log"] = []   # created at runtime, never seeded
    return world
