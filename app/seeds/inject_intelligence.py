"""
Antar — Multi-Dimensional Crime Intelligence Data Injection
========================================================================
Injects 4 spatiotemporal crime clusters into antar.db (via FIRs table)
and fir_synthetic.csv to achieve exactly:
  - 3 HIGH risk alerts (Rajajinagar chain_snatching [existing], Mangaluru cyber_crime, Hubballi burglary)
  - 1 MEDIUM risk alert (Mysuru-Devaraja robbery)
  - 1 LOW risk alert (Kalaburagi theft)
Evenly spread across Karnataka's geographic regions.
"""

import sys
import sqlite3
import datetime
from pathlib import Path

# Force UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.db_path import DB_PATH as _DBP
DB_PATH = Path(_DBP)
CSV_PATH = Path(__file__).parent.parent.parent.parent / "antar-frontend" / "public" / "fir_synthetic.csv"

REF_DATE = datetime.date.fromisoformat("2026-12-28")

def get_week_dates(week_idx: int) -> list[datetime.date]:
    """Return dates falling in trailing week `week_idx` (0 = days 0..6 from REF_DATE)."""
    start_days_ago = week_idx * 7 + 6
    end_days_ago = week_idx * 7
    dates = []
    for d in range(end_days_ago, start_days_ago + 1):
        dates.append(REF_DATE - datetime.timedelta(days=d))
    return dates

def inject():
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Baseline series across weeks 1..13 (sum=25, median=2, MAD=1)
    baseline_counts = [1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3, 2, 1]
    
    clusters = [
        {
            "zone": "Mangaluru",
            "district": "Dakshina Kannada",
            "station": "MNG-01",
            "lat": 12.896181,
            "lon": 74.864846,
            "crime_type": "cyber_crime",
            "act": "IPC 1860 U/s: 420 IT ACT U/s: 66D",
            "week0_count": 9,  # z = (9-2)/1.4826 = 4.72 -> HIGH
            "upi": "mule_king@ybl",
            "ip": "185.220.101.5",
            "veh": "",
            "accused_id": "S0901",
            "mo": "Coordinated cyber-fraud ring. Phishing link sent via fake bank SMS; funds routed via mule_king@ybl."
        },
        {
            "zone": "Hubballi",
            "district": "Dharwad",
            "station": "HBI-01",
            "lat": 15.363573,
            "lon": 75.133178,
            "crime_type": "burglary",
            "act": "IPC 1860 U/s: 457, 380, 454",
            "week0_count": 8,  # z = (8-2)/1.4826 = 4.05 -> HIGH
            "upi": "",
            "ip": "",
            "veh": "KA-25-EA-9988",
            "accused_id": "S0904",
            "mo": "Night shop burglary along Hubballi commercial corridor. Iron grille cut using hydraulic cutter; escape via KA-25-EA-9988."
        },
        {
            "zone": "Mysuru-Devaraja",
            "district": "Mysuru",
            "station": "MYS-01",
            "lat": 12.320713,
            "lon": 76.635459,
            "crime_type": "robbery",
            "act": "IPC 1860 U/s: 392, 397, 34",
            "week0_count": 6,  # z = (6-2)/1.4826 = 2.70 -> MEDIUM
            "upi": "",
            "ip": "",
            "veh": "KA-09-ER-3344",
            "accused_id": "S0002",  # Links to Yellappa M. from P1 pattern
            "mo": "Highway robbery targeting tourists near palace area. Knife threatened; gold chain and cash seized."
        },
        {
            "zone": "Kalaburagi",
            "district": "Kalaburagi",
            "station": "KLB-01",
            "lat": 17.347789,
            "lon": 76.836619,
            "crime_type": "theft",
            "act": "IPC 1860 U/s: 379",
            "week0_count": 5,  # z = (5-2)/1.4826 = 2.02 -> LOW
            "upi": "",
            "ip": "",
            "veh": "KA-32-EF-1122",
            "accused_id": "S0908",
            "mo": "Two-wheeler theft outside agricultural APMC yard. Master key used during afternoon trading hours."
        }
    ]

    print("Starting Intelligence Data Injection...")

    # Get FIRs column headers
    cur.execute("PRAGMA table_info(FIRs)")
    fir_cols = [c[1] for c in cur.fetchall() if c[1] != "id"]
    fir_placeholders = ",".join(["?"] * len(fir_cols))

    new_crimes_count = 0
    csv_rows = []

    for cluster in clusters:
        zone = cluster["zone"]
        dist = cluster["district"]
        stn = cluster["station"]
        lat = cluster["lat"]
        lon = cluster["lon"]
        ctype = cluster["crime_type"]
        act = cluster["act"]
        mo = cluster["mo"]

        # Remove any old records from these target series in trailing 14 weeks from FIRs
        cur.execute("""
            DELETE FROM FIRs 
            WHERE (District_Name = ? OR zone = ?) AND (CrimeGroup_Name = ? OR crime_type = ?) AND (julianday(?) - julianday(date))/7 < 14
        """, (zone, zone, ctype, ctype, REF_DATE.isoformat()))

        # Generate Baseline (Weeks 1..13)
        for w_idx, count in enumerate(baseline_counts, start=1):
            dates = get_week_dates(w_idx)
            for i in range(count):
                occ_date = dates[i % len(dates)]
                fir_no = f"2026-{stn}-{w_idx*100+i+1000}"
                cid = f"CR-INJ-{w_idx}-{stn}-{i}"

                # Insert into FIRs
                fir_row_dict = {
                    "fir_id": cid,
                    "District_Name": zone,
                    "UnitName": stn,
                    "FIR_YEAR": str(occ_date.year),
                    "FIR_MONTH": str(occ_date.month),
                    "FIR_Day": str(occ_date.day),
                    "FIR_Stage": "Closed",
                    "CrimeGroup_Name": ctype,
                    "CrimeHead_Name": ctype.replace("_", " ").title(),
                    "Latitude": str(lat + (i * 0.001)),
                    "Longitude": str(lon + (i * 0.001)),
                    "date": occ_date.isoformat(),
                    "lat_r": round(lat, 2),
                    "lon_r": round(lon, 2),
                    "status": "Closed",
                    "crime_type": ctype,
                    "zone": zone,
                    "station": stn,
                    "FIR_Type": fir_no,
                    "ActSection": act,
                    "IOName": "INSPECTOR RAO (CPI)",
                    "KGID": "100200",
                    "Internal_IO": "OF-101",
                    "Place_of_Offence": f"{zone} Sector {i}",
                    "Distance_from_PS": "2 KM",
                    "Beat_Name": f"{zone} BEAT 1",
                    "Village_Area_Name": zone,
                    "MO_Details": mo,
                    "Accused_ID": cluster["accused_id"],
                    "Vehicle_Reg_No": cluster["veh"],
                    "UPI_ID": cluster["upi"],
                    "IP_Address": cluster["ip"]
                }
                cur.execute(f"INSERT INTO FIRs ({','.join(fir_cols)}) VALUES ({fir_placeholders})",
                            [str(fir_row_dict.get(c, "")) if fir_row_dict.get(c) is not None else "" for c in fir_cols])
                new_crimes_count += 1

        # Generate Week 0 Spike (Current Week ending 2026-12-28)
        w0_dates = get_week_dates(0)
        for i in range(cluster["week0_count"]):
            occ_date = w0_dates[i % len(w0_dates)]
            fir_no = f"2026-{stn}-SPIKE-{i+9000}"
            cid = f"CR-SPIKE-{stn}-{i}"

            fir_row_dict = {
                "fir_id": cid,
                "District_Name": zone,
                "UnitName": stn,
                "FIR_YEAR": str(occ_date.year),
                "FIR_MONTH": str(occ_date.month),
                "FIR_Day": str(occ_date.day),
                "FIR_Stage": "Under Investigation",
                "CrimeGroup_Name": ctype,
                "CrimeHead_Name": ctype.replace("_", " ").title(),
                "Latitude": str(lat + (i * 0.0005)),
                "Longitude": str(lon + (i * 0.0005)),
                "date": occ_date.isoformat(),
                "lat_r": round(lat, 2),
                "lon_r": round(lon, 2),
                "status": "Under Investigation",
                "crime_type": ctype,
                "zone": zone,
                "station": stn,
                "FIR_Type": fir_no,
                "ActSection": act,
                "IOName": "INSPECTOR RAO (CPI)",
                "KGID": "100200",
                "Internal_IO": "OF-101",
                "Place_of_Offence": f"{zone} Commercial Hub",
                "Distance_from_PS": "1.5 KM",
                "Beat_Name": f"{zone} BEAT 1",
                "Village_Area_Name": zone,
                "MO_Details": mo,
                "Accused_ID": cluster["accused_id"],
                "Vehicle_Reg_No": cluster["veh"],
                "UPI_ID": cluster["upi"],
                "IP_Address": cluster["ip"]
            }
            cur.execute(f"INSERT INTO FIRs ({','.join(fir_cols)}) VALUES ({fir_placeholders})",
                        [str(fir_row_dict.get(c, "")) if fir_row_dict.get(c) is not None else "" for c in fir_cols])
            new_crimes_count += 1

            # Build CSV line matching fir_synthetic.csv header exactly
            csv_row = [
                dist, f"{zone} PS", str(occ_date.year), str(occ_date.month), "0", str(occ_date.day),
                "Non Heinous", "Under Investigation", "Written", ctype.upper(), ctype.replace("_", " ").title(),
                str(lat + (i * 0.0005)), str(lon + (i * 0.0005)), f'"{act}"', "INSPECTOR RAO (CPI)", "100200", "",
                f'"{zone} Commercial Hub, {zone}"', "SOUTH FROM PS 1 KM", f"{zone} BEAT 1", zone,
                "1", "0", "0", "0", "0", "1", "2", "1", "0", "1", "0", "0", "1001",
                cluster["accused_id"], cluster["veh"], cluster["upi"], cluster["ip"], f'"{mo}"'
            ]
            csv_rows.append(",".join(csv_row))

    # 2. Inject Suspects, Financial Links, Property, and Crime-Suspects for 360 intelligence
    print("Injecting supporting intelligence links (Suspects, Financial Links, Property)...")
    
    cur.execute("DELETE FROM suspects WHERE suspect_id IN ('S0901', 'S0902', 'S0904', 'S0905', 'S0908')")
    new_suspects = [
        ("S0901", "Vikram Shetty", "Vikki", 29, "M", "PH-CYBER-MNG", "Mangaluru", "cyber broker", 5, "Shetty Sr.", "Indian", "Arrested"),
        ("S0902", "Deepak Kumar", "Deepu", 26, "M", "PH-CYBER-MNG", "Mangaluru", "mule operator", 3, "Kumar Sr.", "Indian", "Absconding"),
        ("S0904", "Shivu Kulkarni", "Highway Shivu", 33, "M", "PH-HUB-BUR", "Hubballi", "mechanic", 7, "Kulkarni Sr.", "Indian", "Arrested"),
        ("S0905", "Basavaraj M.", "Basu", 31, "M", "PH-HUB-BUR", "Hubballi", "driver", 4, "M. Sr.", "Indian", "Absconding"),
        ("S0908", "Ramesh Patil", "Ramya", 25, "M", "PH-KLB-THF", "Kalaburagi", "laborer", 2, "Patil Sr.", "Indian", "Bailed")
    ]
    cur.executemany("""
        INSERT INTO suspects (suspect_id, full_name, alias, age, gender, phone_hash, address_zone, occupation, prior_count, father_name, nationality, arrest_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, new_suspects)

    # Co-accused relationships (source_crime_id instead of source_fir)
    cur.execute("DELETE FROM relationships WHERE suspect_a IN ('S0901', 'S0904') OR suspect_b IN ('S0901', 'S0904')")
    new_rels = [
        ("REL-901", "S0901", "S0902", "co_accused", 5, "CR-SPIKE-MNG-01-0"),
        ("REL-902", "S0904", "S0905", "co_accused", 7, "CR-SPIKE-HBI-01-0"),
        ("REL-903", "S0001", "S0901", "associate", 3, "CR-SPIKE-MNG-01-0")
    ]
    cur.executemany("""
        INSERT INTO relationships (rel_id, suspect_a, suspect_b, rel_type, strength, source_crime_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, new_rels)

    # Financial links
    cur.execute("DELETE FROM financial_links WHERE suspect_id IN ('S0901', 'S0902')")
    new_fin = [
        ("FIN-901", "S0901", "mule_king@ybl", 45, "5L-10L", "phishing_collect_hub"),
        ("FIN-902", "S0902", "185.220.101.5", 112, "10L+", "shared_c2_ip")
    ]
    cur.executemany("""
        INSERT INTO financial_links (link_id, suspect_id, counterparty, txn_count, amount_band, flag_reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, new_fin)

    # Property links (property_id, crime_id, fir_number, property_type, value_inr, status)
    cur.execute("DELETE FROM property WHERE property_type IN ('Cyber Rig', 'Getaway Vehicle') AND value_inr > 150000")
    new_prop = [
        ("PR-MNG-991", "CR-SPIKE-MNG-01-0", "2026-MNG-01-SPIKE-9000", "Cyber Rig", 500000, "Seized"),
        ("PR-HBI-882", "CR-SPIKE-HBI-01-0", "2026-HBI-01-SPIKE-9000", "Getaway Vehicle", 250000, "Seized")
    ]
    cur.executemany("""
        INSERT INTO property (property_id, crime_id, fir_number, property_type, value_inr, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, new_prop)

    # Crime-Suspect links (id, crime_id, suspect_id, role)
    cur.execute("DELETE FROM crime_suspects WHERE suspect_id IN ('S0901', 'S0902', 'S0904', 'S0905', 'S0908')")
    new_cs = [
        ("CS-901", "CR-SPIKE-MNG-01-0", "S0901", "accused"),
        ("CS-902", "CR-SPIKE-MNG-01-0", "S0902", "accused"),
        ("CS-903", "CR-SPIKE-HBI-01-0", "S0904", "accused"),
        ("CS-904", "CR-SPIKE-HBI-01-0", "S0905", "accused"),
        ("CS-905", "CR-SPIKE-KLB-01-0", "S0908", "accused")
    ]
    cur.executemany("""
        INSERT INTO crime_suspects (id, crime_id, suspect_id, role)
        VALUES (?, ?, ?, ?)
    """, new_cs)

    conn.commit()
    conn.close()

    print(f"Successfully inserted {new_crimes_count} crime/FIR records and supporting intelligence into antar.db!")

    # 3. Append to fir_synthetic.csv
    if CSV_PATH.exists() and csv_rows:
        content = CSV_PATH.read_text(encoding="utf-8", errors="ignore")
        if "CR-SPIKE-MNG-01-0" not in content and "mule_king@ybl" not in content:
            with open(CSV_PATH, "a", encoding="utf-8") as f:
                for line in csv_rows:
                    f.write("\n" + line)
            print(f"Appended {len(csv_rows)} Week-0 spike records to {CSV_PATH.name} for 3D Brain visualization!")
        else:
            print(f"ℹWeek-0 records already present in {CSV_PATH.name}, skipping CSV append.")

    # 4. Trigger scan and verify predictions
    print("\nRunning Forecast Agent scan to verify exact alert distribution...")
    from app.agents.forecast_agent import scan
    res = scan(session_id="inject_verify")
    alerts = res.get("alerts", [])
    
    print(f"\nTotal Active Alerts: {len(alerts)}")
    print("--------------------------------------------------------------------------------")
    for a in alerts:
        z = a.get("z_score", 0)
        risk = "HIGH" if z >= 4 else "MEDIUM" if z >= 2.5 else "LOW"
        print(f"[{risk:<6}] {a.get('zone'):<16} | {a.get('crime_type'):<16} | z={z:<6.3f} | obs={a.get('observed')} | band={a.get('conformal_band', {}).get('lo')}-{a.get('conformal_band', {}).get('hi')}")
    print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    inject()
