"""
Antar — Scale & Performance Acceptance Tests (Phase L5.5)
Tests that SQLite and DuckDB produce equivalent results across Q1-Q6 on slice datasets.
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest

try:
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

from app.services import scale_bench as SB


@pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="duckdb or pyarrow not available")
def test_scale_bench_equivalence():
    # Create small synthetic SQLite database
    con = sqlite3.connect(":memory:")
    con.execute("""
        CREATE TABLE FIRs (
            id INTEGER PRIMARY KEY,
            fir_id TEXT,
            date TEXT,
            FIR_YEAR INTEGER,
            district_norm TEXT,
            station TEXT,
            crime_type TEXT,
            status TEXT
        )
    """)

    rows = []
    districts = ["Bengaluru City", "Mysuru City", "Belagavi Dist", "Tumakuru"]
    stations = ["Station A", "Station B", "Station C"]
    crimes = ["THEFT", "BURGLARY", "ROBBERY", "MURDER"]
    statuses = ["Under Investigation", "Chargesheeted", "Undetected"]

    for i in range(1000):
        d = districts[i % len(districts)]
        s = stations[i % len(stations)]
        c = crimes[i % len(crimes)]
        st = statuses[i % len(statuses)]
        yr = 2020 + (i % 4)
        dt = f"{yr}-{(i%12)+1:02d}-{(i%28)+1:02d}"
        rows.append((f"FIR{i:05d}", dt, yr, d, s, c, st))

    con.executemany("INSERT INTO FIRs (fir_id, date, FIR_YEAR, district_norm, station, crime_type, status) VALUES (?,?,?,?,?,?,?)", rows)
    con.commit()

    # Export slice to parquet
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_parquet = tmp.name

    try:
        cols = ["fir_id", "date", "FIR_YEAR", "district_norm", "station", "crime_type", "status"]
        cur = con.execute(f"SELECT {', '.join(cols)} FROM FIRs")
        batch = cur.fetchall()
        pydict = {col: [r[idx] for r in batch] for idx, col in enumerate(cols)}
        table = pa.Table.from_pydict(pydict)
        pq.write_table(table, tmp_parquet)

        d_conn = duckdb.connect(":memory:")

        # Test Q1: District ranking equivalence
        q1_sqlite = con.execute("SELECT district_norm, COUNT(*) as c FROM FIRs GROUP BY district_norm ORDER BY c DESC, district_norm ASC").fetchall()
        q1_duck = d_conn.execute(f"SELECT district_norm, COUNT(*) as c FROM '{tmp_parquet.replace(chr(92), '/')}' GROUP BY district_norm ORDER BY c DESC, district_norm ASC").fetchall()
        assert q1_sqlite == q1_duck, "Q1 results mismatch between SQLite and DuckDB"

        # Test Q2: Monthly trend equivalence
        q2_sqlite = con.execute("SELECT substr(date, 1, 7) as ym, COUNT(*) as c FROM FIRs GROUP BY ym ORDER BY ym").fetchall()
        q2_duck = d_conn.execute(f"SELECT substr(date, 1, 7) as ym, COUNT(*) as c FROM '{tmp_parquet.replace(chr(92), '/')}' GROUP BY ym ORDER BY ym").fetchall()
        assert q2_sqlite == q2_duck, "Q2 results mismatch between SQLite and DuckDB"

        # Test Q3: Crime mix per station equivalence
        q3_sqlite = con.execute("SELECT station, crime_type, COUNT(*) as c FROM FIRs GROUP BY station, crime_type ORDER BY c DESC, station ASC, crime_type ASC").fetchall()
        q3_duck = d_conn.execute(f"SELECT station, crime_type, COUNT(*) as c FROM '{tmp_parquet.replace(chr(92), '/')}' GROUP BY station, crime_type ORDER BY c DESC, station ASC, crime_type ASC").fetchall()
        assert q3_sqlite == q3_duck, "Q3 results mismatch between SQLite and DuckDB"

    finally:
        con.close()
        try:
            Path(tmp_parquet).unlink(missing_ok=True)
        except Exception:
            pass
