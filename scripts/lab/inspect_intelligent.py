import sqlite3

con = sqlite3.connect("intelligent.db")
con.row_factory = sqlite3.Row
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in intelligent.db:", tables)
for t in tables:
    cnt = con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
    print(f"  {t}: {cnt}")
    cur = con.execute(f'SELECT * FROM "{t}" LIMIT 1')
    cols = [d[0] for d in cur.description]
    print(f"    cols: {cols}")
    sample = cur.fetchone()
    if sample:
        d = dict(sample)
        # truncate values for display
        print("    sample:", {k: str(v)[:40] for k, v in d.items()})
con.close()
