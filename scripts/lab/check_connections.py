import sqlite3

con = sqlite3.connect('main_lab.db')
cur = con.cursor()

# Check crime_suspects to FIRs
cur.execute("SELECT count(*) FROM crime_suspects")
total_cs = cur.fetchone()[0]

cur.execute("""
    SELECT count(*) 
    FROM crime_suspects cs 
    JOIN FIRs f ON cs.crime_id = f.FIR_ID
""")
matched_cs = cur.fetchone()[0]

print(f"crime_suspects total: {total_cs:,}, matching FIRs.FIR_ID: {matched_cs:,} ({matched_cs/total_cs*100:.1f}%)")

# Check what crime_id looks like in crime_suspects
sample_cs_crimes = cur.execute("SELECT crime_id FROM crime_suspects LIMIT 10").fetchall()
print("Sample crime_ids in crime_suspects:", sample_cs_crimes)

# Check what FIR_ID looks like in FIRs
sample_firs = cur.execute("SELECT FIR_ID FROM FIRs LIMIT 10").fetchall()
print("Sample FIR_IDs in FIRs:", sample_firs)

# Check relationships to suspects
cur.execute("""
    SELECT count(*) 
    FROM relationships r 
    JOIN suspects s1 ON r.suspect_a = s1.suspect_id
    JOIN suspects s2 ON r.suspect_b = s2.suspect_id
""")
matched_rel = cur.fetchone()[0]
print(f"relationships total: 315, matching both suspects: {matched_rel:,}")

# Check money accounts linked to suspects
cur.execute("""
    SELECT count(*)
    FROM money_accounts a
    JOIN suspects s ON a.suspect_id = s.suspect_id
""")
matched_acc_suspect = cur.fetchone()[0]
print(f"money_accounts with valid suspect_id: {matched_acc_suspect:,}")

# Check money_transactions to money_accounts
cur.execute("""
    SELECT count(*)
    FROM money_transactions t
    JOIN money_accounts a1 ON t.from_account = a1.account_id
    JOIN money_accounts a2 ON t.to_account = a2.account_id
""")
matched_tx = cur.fetchone()[0]
print(f"money_transactions matching accounts on both ends: {matched_tx:,} out of {cur.execute('SELECT count(*) FROM money_transactions').fetchone()[0]:,}")

# Check money_transactions.fir_id to FIRs
cur.execute("""
    SELECT count(*)
    FROM money_transactions t
    JOIN FIRs f ON t.fir_id = f.FIR_ID
""")
matched_tx_fir = cur.fetchone()[0]
print(f"money_transactions matching FIRs.FIR_ID: {matched_tx_fir:,}")
sample_tx_firs = cur.execute("SELECT fir_id FROM money_transactions WHERE fir_id IS NOT NULL LIMIT 5").fetchall()
print("Sample fir_id in money_transactions:", sample_tx_firs)

con.close()
