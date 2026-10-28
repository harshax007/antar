import sqlite3

con = sqlite3.connect('main_lab.db')
cur = con.cursor()

for col in ['story_id', 'Accused_ID', 'Vehicle_Reg_No', 'UPI_ID', 'IP_Address', 'has_synthetic_link', 'is_synthetic_row']:
    cnt = cur.execute(f"SELECT count(*) FROM FIRs WHERE {col} IS NOT NULL AND {col} != '' AND {col} != 0").fetchone()[0]
    print(f"{col:20s}: {cnt:>8,} non-empty rows")

print("\nBreakdown of story_id in FIRs:")
for row in cur.execute("SELECT story_id, count(*) FROM FIRs WHERE story_id IS NOT NULL AND story_id != '' GROUP BY story_id").fetchall():
    print(f"  {row[0]}: {row[1]} rows")

print("\nSample FIRs with story_id:")
for row in cur.execute("SELECT fir_id, story_id, Accused_ID, Vehicle_Reg_No, UPI_ID, IP_Address, District_Name, UnitName FROM FIRs WHERE story_id IS NOT NULL AND story_id != '' LIMIT 5").fetchall():
    print(" ", row)

con.close()
