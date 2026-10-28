import sqlite3
con = sqlite3.connect('main_lab.db')
indexes = con.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='FIRs'").fetchall()
print(f"Total indexes on FIRs: {len(indexes)}")
for n, s in indexes:
    print(f"  {n}: {s}")
con.close()
