"""
Antar — build the Second Brain's FIR corpus (final_backend.md §6 P1-2).

The Brain was running on three planted summaries because embeddings lived only in the
remote Catalyst Data Store and that fetch times out at 20 s. This builds a real,
local, durable corpus from the registry itself.

    python scripts/build_brain_index.py                    # default slice, see --limit
    python scripts/build_brain_index.py --limit 250000
    python scripts/build_brain_index.py --all --yes        # every eligible FIR
    python scripts/build_brain_index.py --stats            # what is indexed today

What gets embedded, per FIR, is the text the registry actually holds:

    CHAIN SNATCHING — THEFT · near the bus stand, Jayanagar, Bengaluru City · 2023-07-14
    MO: two men on a motorcycle snatched a gold chain and fled towards the ring road

`Place_of_Offence` is the substance here: 580,739 rows carry it, 493,988 of them
distinct, averaging 62 characters. That is what makes "chain snatching near a bus stand"
match real cases instead of a demo stub. `MO_Details` is appended where it exists (651
rows) rather than being the only source, which is why the index was empty before.

Cost control, because the budget is 2 GB:
  * 384-dim text embeddings, int8 in SQLite -> 384 bytes a row (100k rows ~ 38 MB).
  * Newest real FIRs first: recency is what case-similarity is usually asked about.
  * Seeded demonstration rows are excluded — the corpus should be the real record.

Re-running is safe: rows are upserted by FIR id, so an interrupted build resumes rather
than duplicating.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

if os.getenv("ANTAR_BRAIN_ONLINE") != "1":                 # same rule as main.py
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# A batch build is exactly the case main.py's thread cap exempts ("a batch refit is
# allowed to use every core it can get"). Embedding is the bottleneck and it scales:
# measured 63 rows/s at one thread, 177/s at eight, while the store writes 15,900/s and
# is never the limit. ANTAR_ONNX_THREADS overrides.
_threads = os.getenv("ANTAR_ONNX_THREADS") or str(max(1, (os.cpu_count() or 2) - 2))
os.environ["ANTAR_ONNX_THREADS"] = _threads
os.environ.setdefault("OMP_NUM_THREADS", _threads)
os.environ.setdefault("OPENBLAS_NUM_THREADS", _threads)
os.environ.setdefault("MKL_NUM_THREADS", _threads)

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 100k rows is ~38 MB on disk and a few MB of working set per query — proportionate to a
# 2 GB box, and enough that similarity search returns real neighbours for any common MO.
DEFAULT_LIMIT = 100_000
BATCH = 256

SELECT_SQL = """
SELECT f.rowid,
       COALESCE(f.CrimeGroup_Name, '')  AS grp,
       COALESCE(f.CrimeHead_Name, '')   AS head,
       COALESCE(f.Place_of_Offence, '') AS place,
       COALESCE(f.Village_Area_Name,'') AS village,
       COALESCE(f.UnitName, '')         AS station,
       COALESCE(f.District_Name, '')    AS district,
       COALESCE(f.date, '')             AS fir_date,
       COALESCE(f.CrimeNo, '')          AS fir_no,
       COALESCE(f.MO_Details, '')       AS mo
  FROM FIRs f
 WHERE COALESCE(f.is_synthetic_row, 0) = 0
   AND (TRIM(COALESCE(f.Place_of_Offence, '')) <> ''
        OR TRIM(COALESCE(f.MO_Details, '')) <> '')
 ORDER BY f.date DESC, f.rowid DESC
"""


def _document(row: sqlite3.Row) -> str:
    """One readable line per FIR. Readable matters: this text is shown to the officer
    as the evidence for a match, not just fed to the model."""
    head = " — ".join(p for p in (row["grp"], row["head"]) if p and p != row["grp"]) or row["grp"]
    where = ", ".join(p for p in (row["place"], row["village"], row["station"],
                                  row["district"]) if p)
    parts = [p for p in (head, where, row["fir_date"]) if p]
    text = " · ".join(parts)
    if row["mo"].strip():
        text += " · MO: " + row["mo"].strip()
    return text[:1200]                       # far past the model's window; keeps rows small


def build(limit: int | None, rebuild: bool) -> int:
    from app.core.db_path import get_db_path
    from app.second_brain import embedder, vec_store

    embedder.load_embedder()
    if embedder._model is None:
        print("embedder unavailable — cannot build the corpus")
        return 1
    backend = getattr(embedder._model, "variant", None)
    print(f"embedder ready ({'onnx/' + backend if backend else 'torch'})")

    if rebuild:
        removed = vec_store.delete(kind="fir")
        print(f"cleared {removed:,} existing FIR rows")

    con = sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True, timeout=60)
    con.row_factory = sqlite3.Row
    try:
        sql = SELECT_SQL + (f" LIMIT {int(limit)}" if limit else "")
        cur = con.execute(sql)
        done = t0 = 0
        t0 = time.time()
        while True:
            rows = cur.fetchmany(BATCH)
            if not rows:
                break
            texts = [_document(r) for r in rows]
            vecs = embedder.embed(texts)                    # document space, 384-dim
            vec_store.upsert([
                {"row_id": f"fir:{r['rowid']}", "kind": "fir", "summary_text": t,
                 "vector": v,
                 "meta": {"fir_no": r["fir_no"], "district": r["district"],
                          "station": r["station"], "crime_group": r["grp"],
                          "date": r["fir_date"], "has_mo": bool(r["mo"].strip())}}
                for r, t, v in zip(rows, texts, vecs)])
            done += len(rows)
            if done % (BATCH * 20) == 0 or len(rows) < BATCH:
                rate = done / max(time.time() - t0, 1e-9)
                print(f"  {done:>8,} rows · {rate:>5.0f}/s · "
                      f"{vec_store.stats()['mb']:>6.1f} MB on disk", flush=True)
    finally:
        con.close()

    # Pack for search: without this every query rebuilds ~100k Python objects from SQL,
    # which measured 1.15 s. Packed and memory-mapped it is a single matrix multiply.
    print("packing for search ...", flush=True)
    packed = vec_store.pack(kind="fir")
    print(f"  packed {packed.get('rows', 0):,} vectors ({packed.get('mb', 0)} MB)")

    s = vec_store.stats()
    print()
    print(f"corpus: {s['rows']:,} rows, {s['mb']} MB at {s['path']}")
    print(f"by tier: {s['by_kind']}")
    print(f"built in {time.time() - t0:.0f}s")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10) + chr(10))[0])
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--all", action="store_true", help="index every eligible FIR")
    ap.add_argument("--rebuild", action="store_true", help="clear the FIR tier first")
    ap.add_argument("--stats", action="store_true", help="print what is indexed and exit")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation for --all")
    args = ap.parse_args()

    from app.second_brain import vec_store
    if args.stats:
        print(vec_store.stats())
        return 0

    limit = None if args.all else args.limit
    if args.all and not args.yes:
        print("--all indexes every eligible FIR (~580k rows, ~220 MB, ~30 min). "
              "Re-run with --yes to confirm.")
        return 2
    return build(limit, args.rebuild)


if __name__ == "__main__":
    sys.exit(main())
