import sqlite3

con = sqlite3.connect('main_lab.db')
cur = con.cursor()
cols = [r[1] for r in cur.execute("PRAGMA table_info(FIRs)").fetchall()]
print(f"FIRs columns ({len(cols)}):", cols)

for pattern in ['CR-EVID-DAC-01', 'KA-22-MB-4545', 'KA-05-EZ-7878', 'KA-04-C-1234', 'S0001', 'S0002', 'S0801', 'ACC-KA-100017', 'KA-25-EH-4471', 'rakesh.pay@ybl', '103.87.44.121']:
    c1 = cur.execute('SELECT count(*) FROM FIRs WHERE FIR_ID LIKE ? OR MO_Details LIKE ?', (f'%{pattern}%', f'%{pattern}%')).fetchone()[0]
    c2 = cur.execute('SELECT count(*) FROM suspects WHERE suspect_id = ? OR full_name LIKE ?', (pattern, f'%{pattern}%')).fetchone()[0]
    c3 = cur.execute('SELECT count(*) FROM ext_entity_keys WHERE key_value LIKE ?', (f'%{pattern}%',)).fetchone()[0]
    c4 = cur.execute('SELECT count(*) FROM crime_suspects WHERE suspect_id = ?', (pattern,)).fetchone()[0]
    print(f'{pattern:18s}: FIRs={c1}, suspects={c2}, entity_keys={c3}, crime_suspects={c4}')

con.close()
