import sqlite3

con = sqlite3.connect('main_lab.db')
cur = con.cursor()

null_cnt = cur.execute("SELECT count(*) FROM money_transactions WHERE fir_id IS NULL").fetchone()[0]
not_null_cnt = cur.execute("SELECT count(*) FROM money_transactions WHERE fir_id IS NOT NULL").fetchone()[0]
print(f"money_transactions with NULL fir_id: {null_cnt:,}, NOT NULL: {not_null_cnt:,}")

distinct_firs = cur.execute("SELECT count(DISTINCT fir_id) FROM money_transactions WHERE fir_id IS NOT NULL").fetchone()[0]
print(f"Distinct fir_ids in money_transactions: {distinct_firs}")

con.close()
