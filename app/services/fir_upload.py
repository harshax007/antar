"""
Antar - adding FIRs from a file (Admin · Data)
==============================================
Three steps, so nothing reaches the register that an admin has not looked at:

  preview(file)      read the CSV, check every row, keep the rows that pass for 15 minutes
  commit(id)         add exactly those rows, record the upload, write it to the audit chain
  undo(batch)        remove an upload's rows again (also on the audit chain)

The file is the KSP FIR export format (template() writes one). A row is refused, with the
reason, when its date is missing, impossible, in the future or outside what this copy
holds; when its district is not a Karnataka district in the register; when its crime
number is already in the register or twice in the file; or when a text field carries
instruction-shaped content (the RAG poisoning screen). Coordinates outside Karnataka are
dropped, not the row: a warning says so.

Derived columns follow the rules the loaded register follows (crime_type is the trimmed
crime group, is_cognizable is 0 only for the non-cognizable groups, CrimeNo is
10001 + unit id + year + a five-digit case number), so an uploaded FIR answers exactly
like a loaded one.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import io
import json
import os
import secrets
import shutil
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta, timezone

from app.core.db_path import DB_PATH, SIDECARS_READ_ONLY as ON_CLOUD, registry_connect

# The official export's columns, in its order. Spaced spellings are what the file uses.
COLUMNS = [
    "District_Name", "UnitName", "FIR_YEAR", "FIR_MONTH", "Offence_Duration", "FIR_Day", "FIR Type",
    "FIR_Stage", "Complaint_Mode", "CrimeGroup_Name", "CrimeHead_Name", "Latitude", "Longitude",
    "ActSection", "IOName", "KGID", "Internal_IO", "Place of Offence", "Distance from PS", "Beat_Name",
    "Village_Area_Name", "Male", "Female", "Boy", "Girl", "Age 0", "VICTIM COUNT", "Accused Count",
    "Arrested Male", "Arrested Female", "Arrested Count\tNo.", "Accused_ChargeSheeted Count",
    "Conviction Count", "Unit_ID",
]
REQUIRED = ("District_Name", "UnitName", "FIR_YEAR", "FIR_MONTH", "FIR_Day", "CrimeGroup_Name")
OPTIONAL_EXTRA = ("CrimeNo",)          # accepted when present; derived when not

# file spelling -> register column
_DB_NAME = {c: c.replace(" ", "_").replace("\t", "_").replace(".", "_") for c in COLUMNS}
_DB_NAME.update({"Arrested Count\tNo.": "Arrested_Count_No_", "Accused_ChargeSheeted Count": "Accused_ChargeSheeted_Count"})

NON_COGNIZABLE = {"MISSING PERSON", "FAILURE TO APPEAR TO COURT", "CRPC"}
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 11.5, 18.5, 74.0, 78.6

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000
# Each FIR costs about 1.3 KB with its indexes. The Cloud copy runs in 1005 MB of /tmp,
# so an upload is refused rather than allowed to fill the disk the database lives on.
BYTES_PER_ROW = 1600
KEEP_FREE = 80 * 1024 * 1024
PREVIEW_TTL_S = 15 * 60

_lock = threading.Lock()
_previews: dict[str, dict] = {}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS upload_batches (
    batch_id TEXT PRIMARY KEY, officer TEXT, filename TEXT, sha256 TEXT,
    rows_added INTEGER, rows_rejected INTEGER, first_date TEXT, last_date TEXT,
    created_at TEXT, status TEXT, undone_by TEXT, undone_at TEXT, undo_reason TEXT);
CREATE TABLE IF NOT EXISTS upload_rows (batch_id TEXT, fir_id TEXT);
CREATE INDEX IF NOT EXISTS ix_upload_rows_batch ON upload_rows(batch_id);
"""


class UploadError(ValueError):
    """A refusal to show the admin as it is."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today_ist() -> date:
    return (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()


def _base_table(con: sqlite3.Connection) -> str:
    """FIRs_all in the Cloud copy (FIRs is a view there), else FIRs."""
    row = con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'FIRs_all'").fetchone()
    return "FIRs_all" if row else "FIRs"


def _covers_from(con: sqlite3.Connection) -> str | None:
    try:
        row = con.execute("SELECT value FROM register_meta WHERE key = 'covers_from'").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def template() -> str:
    """The upload format, with two sample rows to overwrite."""
    d = _today_ist() - timedelta(days=1)
    sample = {c: "" for c in COLUMNS}
    sample.update({"District_Name": "Bengaluru City", "UnitName": "Jayanagar PS", "FIR_YEAR": str(d.year),
                   "FIR_MONTH": str(d.month), "FIR_Day": str(d.day), "FIR Type": "Non Heinous",
                   "FIR_Stage": "Under Investigation", "Complaint_Mode": "Written", "CrimeGroup_Name": "THEFT",
                   "CrimeHead_Name": "Vehicle Theft", "Latitude": "12.9308", "Longitude": "77.5838",
                   "ActSection": "IPC 1860 U/s: 379", "Place of Offence": "SAMPLE ROW - replace with the real place",
                   "Beat_Name": "BEAT 3", "Accused Count": "0", "VICTIM COUNT": "1", "Unit_ID": ""})
    second = dict(sample, UnitName="Hubballi Town PS", District_Name="Hubballi Dharwad City",
                  CrimeGroup_Name="CYBER CRIME", CrimeHead_Name="Online Fraud", ActSection="IT ACT 2000 U/s: 66(D)",
                  Latitude="15.3647", Longitude="75.1240")
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=COLUMNS + list(OPTIONAL_EXTRA), lineterminator="\n")
    w.writeheader()
    w.writerow(sample)
    w.writerow(second)
    return out.getvalue()


def _known(con: sqlite3.Connection) -> dict:
    """Districts, their units and unit ids, crime groups - what a row is checked against."""
    t = _base_table(con)
    districts: dict[str, str] = {}
    units: dict[str, dict[str, str]] = {}
    for dist, unit, uid in con.execute(
            f"SELECT District_Name, UnitName, MAX(Unit_ID) FROM {t} WHERE is_synthetic_row = 0 "
            f"GROUP BY District_Name, UnitName"):
        if not dist:
            continue
        districts[dist.strip().upper()] = dist
        units.setdefault(dist.strip().upper(), {})[(unit or "").strip().upper()] = str(uid or "")
    groups = {(g or "").strip().upper() for (g,) in con.execute(
        f"SELECT DISTINCT CrimeGroup_Name FROM {t} WHERE is_synthetic_row = 0")}
    return {"districts": districts, "units": units, "groups": groups}


def _int(v, lo: int, hi: int) -> int | None:
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def _float(v) -> float | None:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def preview(content: bytes, filename: str, officer: str) -> dict:
    if len(content) > MAX_BYTES:
        raise UploadError(f"The file is larger than {MAX_BYTES // 1048576} MB. Split it and upload the parts.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UploadError("The file is not UTF-8 text. Save it as 'CSV UTF-8' and try again.")
    reader = csv.DictReader(io.StringIO(text))
    headers = [h for h in (reader.fieldnames or []) if h is not None]
    if not headers:
        raise UploadError("The file has no header row.")
    norm = {h.strip(): h for h in headers}
    # a tab inside "Arrested Count\tNo." is easily lost in editing; accept the spaced form too
    if "Arrested Count No." in norm and "Arrested Count\tNo." not in norm:
        norm["Arrested Count\tNo."] = norm["Arrested Count No."]
    missing = [c for c in REQUIRED if c not in norm]
    if missing:
        raise UploadError("Required columns are missing: " + ", ".join(missing)
                          + ". Download the template for the exact column names.")
    columns = [{"column": c, "found": c in norm, "required": c in REQUIRED} for c in COLUMNS]
    ignored = [h for h in headers if h.strip() not in COLUMNS and h.strip() not in OPTIONAL_EXTRA
               and h.strip() != "Arrested Count No."]

    from app.core.rag_security import detect_injection, normalize_untrusted

    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        known = _known(con)
        covers = _covers_from(con)
        t = _base_table(con)
        rows_in = list(reader)
        # one scan for every crime number the file names (CrimeNo has no index)
        named = sorted({(r.get(norm["CrimeNo"]) or "").strip() for r in rows_in} - {""}) if "CrimeNo" in norm else []
        existing = {c for (c,) in con.execute(
            f"SELECT CrimeNo FROM {t} WHERE CrimeNo IN (SELECT value FROM json_each(?))",
            (json.dumps(named),))} if named else set()
        today = _today_ist()
        ready, rejected, warnings = [], [], []
        seen: set[str] = set()
        for n, raw in enumerate(rows_in, start=2):          # row 1 is the header
            if len(ready) + len(rejected) >= MAX_ROWS:
                warnings.append({"row": n, "issue": f"Only the first {MAX_ROWS:,} rows are read in one upload."})
                break
            row = {c: (raw.get(norm[c]) or "").strip() if c in norm else "" for c in COLUMNS}
            for c in OPTIONAL_EXTRA:
                row[c] = (raw.get(norm[c]) or "").strip() if c in norm else ""
            why = []
            y, m, d = _int(row["FIR_YEAR"], 1990, 2100), _int(row["FIR_MONTH"], 1, 12), _int(row["FIR_Day"], 1, 31)
            when = None
            if y and m and d:
                try:
                    when = date(y, m, d)
                except ValueError:
                    why.append("the date does not exist")
            else:
                why.append("year, month or day is missing or not a number")
            if when and when > today:
                why.append(f"the date {when:%d %b %Y} is in the future")
            if when and covers and when.isoformat() < covers:
                why.append(f"this online copy holds FIRs from {date.fromisoformat(covers):%d %b %Y} on")
            dkey = row["District_Name"].upper()
            district = known["districts"].get(dkey)
            if not district:
                near = difflib.get_close_matches(dkey, list(known["districts"]), n=1, cutoff=0.6)
                why.append(f"'{row['District_Name'] or '(blank)'}' is not a district in the register"
                           + (f" - did you mean {known['districts'][near[0]]}?" if near else ""))
            if not row["UnitName"]:
                why.append("the police station (UnitName) is blank")
            if not row["CrimeGroup_Name"]:
                why.append("the crime group is blank")
            text_fields = " | ".join(row[c] for c in ("UnitName", "CrimeGroup_Name", "CrimeHead_Name", "ActSection",
                                                      "Place of Offence", "Village_Area_Name", "Beat_Name", "IOName"))
            if detect_injection(text_fields):
                why.append("a text field contains instruction-like content and was held back")
            crime_no = row["CrimeNo"]
            if crime_no:
                if crime_no in seen:
                    why.append(f"crime number {crime_no} appears twice in this file")
                elif crime_no in existing:
                    why.append(f"crime number {crime_no} is already in the register")
                seen.add(crime_no)
            if why:
                rejected.append({"row": n, "reasons": why,
                                 "summary": f"{row['District_Name']} · {row['UnitName']} · {row['CrimeGroup_Name']}"})
                continue
            if row["CrimeGroup_Name"].strip().upper() not in known["groups"]:
                warnings.append({"row": n, "issue": f"crime group '{row['CrimeGroup_Name']}' is new to the register; it is kept as written"})
            unit_key = row["UnitName"].upper()
            unit_id = row["Unit_ID"] or known["units"].get(dkey, {}).get(unit_key, "")
            if unit_key not in known["units"].get(dkey, {}):
                warnings.append({"row": n, "issue": f"'{row['UnitName']}' is a new station for {district}"})
            lat, lon = _float(row["Latitude"]), _float(row["Longitude"])
            if (row["Latitude"] or row["Longitude"]) and not (lat and lon and LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                warnings.append({"row": n, "issue": "the coordinates are outside Karnataka; the row is kept without a map point"})
                lat = lon = None
            clean = {c: normalize_untrusted(v, max_len=500) for c, v in row.items()}
            clean.update({"District_Name": district, "Unit_ID": unit_id, "_date": when.isoformat(),
                          "_lat": lat, "_lon": lon, "_row": n})
            ready.append(clean)
    finally:
        con.close()

    pid = secrets.token_urlsafe(12)
    sha = hashlib.sha256(content).hexdigest()
    with _lock:
        for k in [k for k, v in _previews.items() if v["expires"] < time.time()]:
            _previews.pop(k, None)
        _previews[pid] = {"rows": ready, "filename": filename, "sha256": sha, "officer": officer,
                          "rejected": len(rejected), "expires": time.time() + PREVIEW_TTL_S}
    dates = sorted(r["_date"] for r in ready)
    sample_cols = ("_date", "District_Name", "UnitName", "CrimeGroup_Name", "CrimeHead_Name", "FIR_Stage")
    return {
        "preview_id": pid, "filename": filename, "sha256": sha,
        "rows_read": len(ready) + len(rejected), "rows_ready": len(ready), "rows_rejected": len(rejected),
        "first_date": dates[0] if dates else None, "last_date": dates[-1] if dates else None,
        "columns": columns, "ignored_columns": ignored,
        "sample": [{("date" if k == "_date" else k): r[k] for k in sample_cols} for r in ready[:5]],
        "rejected": rejected[:200], "warnings": warnings[:200],
        "space": _space(len(ready)),
        "expires_in_s": PREVIEW_TTL_S,
        "covers_from": covers,
        # the Cloud copy unpacks the register from the image at each start: what is added
        # here lasts until the server restarts. Said before the admin adds anything.
        "lasts_until_restart": bool(ON_CLOUD),
    }


def _space(rows: int) -> dict:
    free = shutil.disk_usage(os.path.dirname(os.path.abspath(DB_PATH)) or ".").free
    need = rows * BYTES_PER_ROW
    return {"free_mb": round(free / 1048576), "needed_mb": round(need / 1048576, 1),
            "fits": free - need >= KEEP_FREE}


def _ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(_SCHEMA)


def _next_ids(con: sqlite3.Connection, t: str, n: int) -> list[int]:
    """Loaded FIRs carry id = the number in their fir_id (K1526329 has id 1526329).

    A number an upload once used is never handed out again, even after that upload was
    removed: the audit chain still names those FIRs, and must keep meaning the same ones.
    """
    top = max(con.execute(f"SELECT MAX(id) FROM {t}").fetchone()[0] or 0,
              con.execute("SELECT MAX(CAST(substr(fir_id, 2) AS INTEGER)) FROM upload_rows").fetchone()[0] or 0)
    return list(range(int(top) + 1, int(top) + n + 1))


def commit(preview_id: str, officer: str, role: str) -> dict:
    with _lock:
        p = _previews.get(preview_id)
        if not p or p["expires"] < time.time():
            _previews.pop(preview_id, None)
            raise UploadError("This check has expired or was already used. Check the file again.")
        if p["officer"] != officer:
            raise UploadError("Only the officer who checked the file can add it.")
        _previews.pop(preview_id, None)
    rows = p["rows"]
    if not rows:
        raise UploadError("No row passed the checks, so there is nothing to add.")
    space = _space(len(rows))
    if not space["fits"]:
        raise UploadError(f"Not enough space: this upload needs about {space['needed_mb']} MB and the server "
                          f"must keep {KEEP_FREE // 1048576} MB free ({space['free_mb']} MB free now). Upload fewer rows.")

    batch = "UP-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    con = registry_connect(DB_PATH, timeout=60)
    try:
        _ensure_schema(con)
        t = _base_table(con)
        have = {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
        nums = _next_ids(con, t, len(rows))
        ids = [f"K{n}" for n in nums]
        # the last case number per station and year, in one scan
        want = sorted({(str(r["Unit_ID"]), r["_date"][:4]) for r in rows if r["Unit_ID"] and not r["CrimeNo"]})
        seq: dict[tuple, int] = {}
        if want:
            for uid, yr, top in con.execute(
                    f"SELECT CAST(Unit_ID AS TEXT), FIR_YEAR, MAX(CAST(CaseNo AS INTEGER)) FROM {t} "
                    f"WHERE CAST(Unit_ID AS TEXT) || '|' || FIR_YEAR IN (SELECT value FROM json_each(?)) "
                    f"GROUP BY 1, 2", (json.dumps([f"{u}|{y}" for u, y in want]),)):
                seq[(uid, yr)] = int(top or 0)
        records = []
        for num, fid, r in zip(nums, ids, rows):
            year = r["_date"][:4]
            crime_no = r["CrimeNo"]
            case_no = ""
            if not crime_no and r["Unit_ID"]:
                key = (str(r["Unit_ID"]), year)
                seq[key] = max(seq.get(key, 0), int(year) * 100000) + 1
                case_no = str(seq[key])
                crime_no = f"10001{r['Unit_ID']}{case_no}"
            group = r["CrimeGroup_Name"].strip()
            rec = {_DB_NAME[c]: r[c] for c in COLUMNS}
            rec.update({
                "id": num, "fir_id": fid, "CrimeNo": crime_no, "CaseNo": case_no, "District_Name": r["District_Name"],
                "FIR_YEAR": year, "FIR_MONTH": str(int(r["_date"][5:7])), "FIR_Day": str(int(r["_date"][8:10])),
                "Latitude": r["_lat"], "Longitude": r["_lon"], "location_lat": r["_lat"], "location_lon": r["_lon"],
                "lat_r": round(r["_lat"], 2) if r["_lat"] is not None else None,
                "lon_r": round(r["_lon"], 2) if r["_lon"] is not None else None,
                "zone": r["District_Name"], "district_norm": r["District_Name"], "station": r["UnitName"],
                "date": r["_date"], "crime_type": group, "status": r["FIR_Stage"] or "Under Investigation",
                "FIR_Stage": r["FIR_Stage"] or "Under Investigation",
                "is_cognizable": 0 if group.upper() in NON_COGNIZABLE else 1,
                "is_synthetic_row": 0, "has_synthetic_link": 0,
            })
            records.append({k: v for k, v in rec.items() if k in have})
        cols = sorted({k for rec in records for k in rec})
        con.executemany(f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                        [[rec.get(c) for c in cols] for rec in records])
        con.executemany("INSERT INTO upload_rows (batch_id, fir_id) VALUES (?, ?)", [(batch, f) for f in ids])
        dates = sorted(r["_date"] for r in rows)
        con.execute("INSERT INTO upload_batches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (batch, officer, p["filename"], p["sha256"], len(rows), p["rejected"], dates[0], dates[-1],
                     _now(), "added", None, None, None))
        con.commit()
    finally:
        con.close()
    _after_change()
    _audit("data_upload", batch, officer, role, f"{len(rows)} FIRs from {p['filename']} (sha256 {p['sha256'][:16]})")
    return {"batch_id": batch, "rows_added": len(rows), "first_fir": ids[0], "last_fir": ids[-1],
            "first_date": dates[0], "last_date": dates[-1]}


def history(limit: int = 50) -> list[dict]:
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        con.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in con.execute(
                "SELECT * FROM upload_batches ORDER BY created_at DESC LIMIT ?", (limit,))]
        except sqlite3.OperationalError:
            return []                                   # no upload yet: the table does not exist
    finally:
        con.close()


def undo(batch_id: str, officer: str, role: str, reason: str) -> dict:
    reason = " ".join((reason or "").split())[:300]
    if len(reason) < 5:
        raise UploadError("Write a short reason for removing this upload.")
    con = registry_connect(DB_PATH, timeout=60)
    try:
        _ensure_schema(con)
        row = con.execute("SELECT status FROM upload_batches WHERE batch_id = ?", (batch_id,)).fetchone()
        if not row:
            raise UploadError("No such upload.")
        if row[0] != "added":
            raise UploadError("This upload was already removed.")
        t = _base_table(con)
        n = con.execute(f"DELETE FROM {t} WHERE fir_id IN (SELECT fir_id FROM upload_rows WHERE batch_id = ?)",
                        (batch_id,)).rowcount
        con.execute("UPDATE upload_batches SET status = 'removed', undone_by = ?, undone_at = ?, undo_reason = ? "
                    "WHERE batch_id = ?", (officer, _now(), reason, batch_id))
        con.commit()
    finally:
        con.close()
    _after_change()
    _audit("data_upload_removed", batch_id, officer, role, f"{n} FIRs removed: {reason}")
    return {"batch_id": batch_id, "rows_removed": n}


def _after_change() -> None:
    """Answers are cached; the register just changed under them."""
    try:
        from app.agents.query_agent import clear_query_cache
        from app.services import zcql_local, product_store
        clear_query_cache()
        zcql_local._RESULT_CACHE.clear()
        zcql_local._VIRTUAL_CACHE.clear()
        product_store.invalidate("briefing:shift:")
    except Exception as e:                              # a stale cache never undoes an upload
        print(f"[fir_upload] cache refresh skipped: {e}")


def _audit(event: str, batch_id: str, officer: str, role: str, detail: str) -> None:
    try:
        from app.services import audit_store
        audit_store.record_data_event(event, batch_id=batch_id, officer=officer, role=role, detail=detail)
    except Exception as e:
        print(f"[fir_upload] audit write failed: {e}")
