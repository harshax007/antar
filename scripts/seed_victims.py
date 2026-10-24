"""
Link victims to FIRs: one row per victim, for every FIR that records victims.

    python scripts/seed_victims.py

Each FIR records how many victims it had, split into men, women, boys and girls (Male, Female,
Boy, Girl; VICTIM_COUNT when the split is missing). This builds the `victims` table to match
those counts exactly, so a victim's sex and adult/child status always agree with the FIR. Age
band, occupation and relation to the accused are generated per crime group. The table keeps
the columns chat's victim template already reads (victim_id, age_band, gender, occupation,
zone) and adds fir_id, crime_type, district, age_group and relation.

The previous `victims` table (district-level rows with no FIR) is kept as
victims_unlinked_20261024, not deleted. Deterministic per FIR, idempotent, source='seeded'.
"""
from __future__ import annotations

import hashlib
import os
import random
import sqlite3
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.db_path import DB_PATH  # noqa: E402

OLD = "victims_unlinked_20261024"
MAX_PER_FIR = 25
ADULT_BANDS = ["18-24", "25-34", "35-44", "45-59", "60+"]
ADULT_W = [22, 32, 22, 16, 8]
OCC_FALLBACK = {"M": ["daily wage", "farmer", "driver", "shopkeeper", "salaried", "student", "labourer", "self-employed"],
                "F": ["homemaker", "daily wage", "salaried", "student", "farmer", "shopkeeper", "domestic worker"]}

# relation to the accused, by what the crime is (keyword in the crime group or head)
RELATIONS = [
    (("CRUELTY", "DOWRY", "HUSBAND", "DOMESTIC"), [("spouse", 60), ("in-laws", 30), ("family", 10)]),
    (("POCSO", "RAPE", "SEXUAL", "MOLEST", "WOMEN", "OUTRAG"), [("acquaintance", 45), ("family", 20), ("neighbour", 15), ("stranger", 20)]),
    (("MURDER", "HURT", "ASSAULT", "ATTEMPT"), [("acquaintance", 40), ("family", 20), ("neighbour", 15), ("stranger", 25)]),
    (("CHEAT", "FRAUD", "CYBER", "FORGERY"), [("stranger, online", 55), ("acquaintance", 25), ("business contact", 20)]),
    (("ACCIDENT", "MOTOR", "ROAD", "VEHICLES"), [("stranger", 100)]),
    (("THEFT", "BURGLARY", "ROBBERY", "DACOITY", "SNATCH", "HOUSE BREAK"), [("stranger", 85), ("acquaintance", 10), ("employee", 5)]),
    (("KIDNAP", "ABDUCT", "MISSING"), [("acquaintance", 50), ("stranger", 30), ("family", 20)]),
]


def _relation(rnd: random.Random, crime: str) -> str:
    c = (crime or "").upper()
    for keys, opts in RELATIONS:
        if any(k in c for k in keys):
            names, weights = zip(*opts)
            return rnd.choices(names, weights)[0]
    return rnd.choices(["stranger", "acquaintance", "neighbour", "family"], [50, 30, 12, 8])[0]


def _occupations(con) -> dict:
    """Occupation mix by sex, from the previous victims table where it exists."""
    occ = defaultdict(list)
    try:
        for g, o, n in con.execute(f"SELECT gender, occupation, COUNT(*) FROM {OLD} GROUP BY 1, 2"):
            if g in ("M", "F") and o:
                occ[g].append((o, n))
    except sqlite3.Error:
        pass
    return {g: occ.get(g) or [(o, 1) for o in OCC_FALLBACK[g]] for g in ("M", "F")}


def build(con: sqlite3.Connection) -> dict:
    t0 = time.time()
    have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if OLD not in have and "victims" in have:
        cols = {r[1] for r in con.execute("PRAGMA table_info(victims)")}
        if "fir_id" not in cols:                       # the old, unlinked table: keep it
            con.execute(f"ALTER TABLE victims RENAME TO {OLD}")
    con.execute("DROP TABLE IF EXISTS victims")
    con.execute("""CREATE TABLE victims (
        victim_id   TEXT PRIMARY KEY,
        fir_id      TEXT NOT NULL,
        zone        TEXT,
        district    TEXT,
        crime_type  TEXT,
        gender      TEXT,          -- M | F
        age_group   TEXT,          -- adult | child
        age_band    TEXT,
        occupation  TEXT,
        relation    TEXT,          -- relation to the accused
        source      TEXT NOT NULL DEFAULT 'seeded')""")
    occ = _occupations(con)
    occ_names = {g: [o for o, _ in v] for g, v in occ.items()}
    occ_w = {g: [n for _, n in v] for g, v in occ.items()}

    rows, n_firs = [], 0
    cur = con.execute(
        "SELECT fir_id, zone, COALESCE(district_norm, District_Name), crime_type, "
        "COALESCE(CrimeGroup_Name, '') || ' ' || COALESCE(CrimeHead_Name, ''), "
        "COALESCE(Male,0), COALESCE(Female,0), COALESCE(Boy,0), COALESCE(Girl,0), COALESCE(VICTIM_COUNT,0) "
        "FROM FIRs WHERE COALESCE(VICTIM_COUNT,0) > 0 OR COALESCE(Male,0) + COALESCE(Female,0) + COALESCE(Boy,0) + COALESCE(Girl,0) > 0")
    ins = con.cursor()
    for fir, zone, district, ctype, crime, m, f, b, g, vc in cur:
        rnd = random.Random(int(hashlib.sha1(str(fir).encode()).hexdigest()[:12], 16))
        people = [("M", "adult")] * int(m) + [("F", "adult")] * int(f) + [("M", "child")] * int(b) + [("F", "child")] * int(g)
        if not people:
            people = [(rnd.choice("MF"), "adult") for _ in range(int(vc))]
        n_firs += 1
        for k, (sex, grp) in enumerate(people[:MAX_PER_FIR], 1):
            if grp == "child":
                band = rnd.choices(["0-11", "12-17"], [35, 65])[0]
                job = "student" if band == "12-17" else "child"
            else:
                band = rnd.choices(ADULT_BANDS, ADULT_W)[0]
                job = rnd.choices(occ_names[sex], occ_w[sex])[0]
                if band == "60+" and rnd.random() < 0.5:
                    job = "retired"
            rows.append((f"V-{fir}-{k}", fir, zone, district, ctype, sex, grp, band, job, _relation(rnd, crime), "seeded"))
        if len(rows) >= 50000:
            ins.executemany("INSERT INTO victims VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
            rows = []
    if rows:
        ins.executemany("INSERT INTO victims VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute("CREATE INDEX idx_victims_fir ON victims(fir_id)")
    con.execute("CREATE INDEX idx_victims_zone_ct ON victims(zone, crime_type)")
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM victims").fetchone()[0]
    return {"victims": total, "firs": n_firs, "seconds": round(time.time() - t0, 1)}


if __name__ == "__main__":
    con = sqlite3.connect(DB_PATH, timeout=60)
    try:
        print(build(con))
    finally:
        con.close()
