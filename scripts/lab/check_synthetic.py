import sqlite3

con = sqlite3.connect('main_lab.db')
cur = con.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"Total tables: {len(tables)}")
for (t,) in tables:
    try:
        cnt = cur.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        print(f"{t:35s}: {cnt:>10,}")
    except Exception as e:
        print(f"{t:35s}: ERROR ({e})")
con.close()
