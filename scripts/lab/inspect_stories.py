import sqlite3
import sys

con = sqlite3.connect('main_lab.db')
con.row_factory = sqlite3.Row
rows = con.execute('SELECT * FROM dim_storyline').fetchall()
print(f"Total storylines: {len(rows)}")
for r in rows:
    d = dict(r)
    print(f"\n[{d['story_id']}] {d['title_en']}")
    print(f"  Capability: {d['capability']} | Key: {d['shared_key']} = {d['key_value']} | Districts: {d['n_districts']} | FIRs: {d['n_firs']}")
    print(f"  Question EN: {d['question_en']}")
    print(f"  Expected finding: {d['expected_finding']}")
    print(f"  Provenance: {d['provenance']}")
con.close()
