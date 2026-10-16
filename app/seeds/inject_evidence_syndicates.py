"""
Antar — Non-Cyber Evidence & Syndicate Data Injection
========================================================================
Injects 5 multi-dimensional non-cyber crime syndicates (with 6-8 FIRs each)
into antar.db (FIRs table) and fir_synthetic.csv to provide prominent, top-ranked
physical, biometric, and relational evidence callout labels on the 3D Brain Globe:
  1. Interstate Highway Dacoity & Murder Syndicate (7 FIRs -> Bheema the Butcher network)
  2. Gold Snatching & Pawnbroker Laundering Ring (8 FIRs -> Robbery ring · KA-05-EZ-7878)
  3. Narcotic Drug Corridor & Extortion Ring (7 FIRs -> Zaid Khan network)
  4. Temple Burglary & Antique Smuggling Network (6 FIRs -> Burglary ring · KA-04-C-1234)
  5. Interstate Arms Trafficking & Rioting Syndicate (6 FIRs -> Rudre Gowda network)

These historical syndicates enrich the 3D Brain Globe without altering the live
short-horizon 3 HIGH, 1 MEDIUM, 1 LOW alert balance.
"""

import sys
import sqlite3
import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.db_path import DB_PATH as _DBP
DB_PATH = Path(_DBP)
CSV_PATH = Path(__file__).parent.parent.parent.parent / "antar-frontend" / "public" / "fir_synthetic.csv"

def inject_evidence():
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    print("Starting Non-Cyber Evidence & Syndicate Injection (6-8 FIRs per ring)...")

    cur.execute("PRAGMA table_info(FIRs)")
    fir_cols = [c[1] for c in cur.fetchall() if c[1] != "id"]
    fir_placeholders = ",".join(["?"] * len(fir_cols))

    syndicates = []

    # 1. Interstate Highway Dacoity & Murder (7 FIRs across Belagavi, Dharwad, Hubballi) -> Bheema the Butcher network
    for i, (zone, dist, stn, lat, lon, ctype, date) in enumerate([
        ("Belagavi", "Belagavi", "BLR-BEL-01", 15.8497, 74.4977, "dacoity", "2026-05-14"),
        ("Belagavi", "Belagavi", "BLR-BEL-01", 15.8520, 74.5010, "dacoity", "2026-06-02"),
        ("Belagavi", "Belagavi", "BLR-BEL-02", 15.8450, 74.4920, "robbery", "2026-06-25"),
        ("Dharwad", "Dharwad", "DWD-01", 15.4589, 75.0078, "dacoity", "2026-07-11"),
        ("Dharwad", "Dharwad", "DWD-02", 15.4620, 75.0120, "robbery", "2026-08-05"),
        ("Hubballi", "Dharwad", "HBI-01", 15.3647, 75.1240, "murder", "2026-08-22"),
        ("Hubballi", "Dharwad", "HBI-01", 15.3680, 75.1280, "dacoity", "2026-09-10"),
    ]):
        syndicates.append({
            "cid": f"CR-EVID-DAC-{i+1:02d}",
            "fir_no": f"2026-NH48-DAC-80{i+1}",
            "zone": zone, "dist": dist, "stn": stn, "lat": lat, "lon": lon,
            "ctype": ctype, "group": ctype.upper(),
            "act": "IPC 1860 U/s: 395, 397, 302 Arms Act U/s: 25",
            "date": date, "stage": "charge_sheeted",
            "place": "NH-48 Highway Toll Corridor, Belagavi-Hubballi Circuit",
            "veh": "KA-22-MB-4545", "accused_id": "S0801",
            "mo": f"Interstate highway dacoity/robbery #{i+1} on NH-48. Night interception using spike strips; armed intimidation with country-made pistols; escape via Scorpio KA-22-MB-4545."
        })

    # 2. Gold Snatching & Pawnbroker Laundering Ring (8 FIRs across Jayanagar, Banashankari, JP Nagar) -> Robbery ring · KA-05-EZ-7878
    for i, (zone, dist, stn, lat, lon, ctype, date) in enumerate([
        ("Jayanagar", "Bengaluru City", "BLR-JYN-01", 12.9250, 77.5800, "robbery", "2026-04-10"),
        ("Jayanagar", "Bengaluru City", "BLR-JYN-01", 12.9280, 77.5830, "chain_snatching", "2026-04-28"),
        ("Banashankari", "Bengaluru City", "BLR-BSK-01", 12.9255, 77.5750, "chain_snatching", "2026-05-15"),
        ("Banashankari", "Bengaluru City", "BLR-BSK-01", 12.9220, 77.5710, "robbery", "2026-06-03"),
        ("JP Nagar", "Bengaluru City", "BLR-JPN-01", 12.9063, 77.5857, "chain_snatching", "2026-06-20"),
        ("JP Nagar", "Bengaluru City", "BLR-JPN-01", 12.9090, 77.5880, "robbery", "2026-07-08"),
        ("Basavanagudi", "Bengaluru City", "BLR-BAS-01", 12.9421, 77.5755, "chain_snatching", "2026-07-25"),
        ("Basavanagudi", "Bengaluru City", "BLR-BAS-01", 12.9450, 77.5790, "chain_snatching", "2026-08-12"),
    ]):
        syndicates.append({
            "cid": f"CR-EVID-ROB-{i+1:02d}",
            "fir_no": f"2026-SOUTH-ROB-81{i+1}",
            "zone": zone, "dist": dist, "stn": stn, "lat": lat, "lon": lon,
            "ctype": ctype, "group": ctype.upper().replace("_", " "),
            "act": "IPC 1860 U/s: 392, 356, 379 BNS U/s: 304",
            "date": date, "stage": "Convicted",
            "place": "South Bengaluru Metro Corridor, Jayanagar-BSK Circuit",
            "veh": "KA-05-EZ-7878", "accused_id": "S0803",
            "mo": f"High-speed robbery/snatching #{i+1} near metro pillars. KTM Duke KA-05-EZ-7878 used for rapid approach; stolen gold chains transferred within 30 mins to receiver Suresh Jain."
        })

    # 3. Narcotic Drug Corridor & Club Extortion Ring (7 FIRs across Indiranagar, Koramangala, Mysuru) -> Zaid Khan network
    for i, (zone, dist, stn, lat, lon, ctype, date) in enumerate([
        ("Indiranagar", "Bengaluru City", "BLR-IND-01", 12.9784, 77.6408, "narcotics", "2026-05-05"),
        ("Indiranagar", "Bengaluru City", "BLR-IND-01", 12.9810, 77.6430, "narcotics", "2026-05-22"),
        ("Koramangala", "Bengaluru City", "BLR-KOR-01", 12.9352, 77.6245, "narcotics", "2026-06-10"),
        ("Koramangala", "Bengaluru City", "BLR-KOR-01", 12.9380, 77.6270, "extortion", "2026-06-28"),
        ("Whitefield", "Bengaluru City", "BLR-WFD-01", 12.9698, 77.7499, "narcotics", "2026-07-15"),
        ("Mysuru-Nazarbad", "Mysuru", "MYS-02", 12.3052, 76.6629, "extortion", "2026-08-01"),
        ("Mysuru-Nazarbad", "Mysuru", "MYS-02", 12.3080, 76.6660, "narcotics", "2026-08-18"),
    ]):
        syndicates.append({
            "cid": f"CR-EVID-NDP-{i+1:02d}",
            "fir_no": f"2026-PUB-NDP-82{i+1}",
            "zone": zone, "dist": dist, "stn": stn, "lat": lat, "lon": lon,
            "ctype": ctype, "group": ctype.upper(),
            "act": "NDPS ACT 1985 U/s: 20(b), 22, 27A IPC U/s: 384, 386",
            "date": date, "stage": "Under Investigation",
            "place": "100 Feet Road Pub Corridor & Lounge Circuit",
            "veh": "KA-01-MQ-0007", "accused_id": "S0805",
            "mo": f"Nightlife drug distribution/extortion #{i+1}. MDMA and cocaine transported in floorboards of Fortuner KA-01-MQ-0007; protection extorted from pub owners by Zaid Khan."
        })

    # 4. Heritage Temple Burglary & Antique Smuggling (6 FIRs across Hebbal, Yelahanka, Tumakuru, Hubballi) -> Burglary ring · KA-04-C-1234
    for i, (zone, dist, stn, lat, lon, ctype, date) in enumerate([
        ("Hebbal", "Bengaluru City", "BLR-HEB-01", 13.0358, 77.5970, "burglary", "2026-03-15"),
        ("Hebbal", "Bengaluru City", "BLR-HEB-01", 13.0380, 77.6000, "theft", "2026-04-02"),
        ("Yelahanka", "Bengaluru City", "BLR-YEL-01", 13.1007, 77.5963, "burglary", "2026-04-20"),
        ("Tumakuru", "Tumakuru", "TMK-01", 13.3379, 77.1173, "burglary", "2026-05-08"),
        ("Hubballi", "Dharwad", "HBI-02", 15.3500, 75.1300, "theft", "2026-05-26"),
        ("Hubballi", "Dharwad", "HBI-02", 15.3530, 75.1330, "burglary", "2026-06-12"),
    ]):
        syndicates.append({
            "cid": f"CR-EVID-BUR-{i+1:02d}",
            "fir_no": f"2026-TMP-BUR-83{i+1}",
            "zone": zone, "dist": dist, "stn": stn, "lat": lat, "lon": lon,
            "ctype": ctype, "group": ctype.upper(),
            "act": "IPC 1860 U/s: 457, 380 Antiquities Act U/s: 25",
            "date": date, "stage": "charge_sheeted",
            "place": "Heritage Temple Circuit, North Corridor",
            "veh": "KA-04-C-1234", "accused_id": "S0807",
            "mo": f"Heritage temple burglary #{i+1}. Perimeter CCTV disabled with wireless jammers; ancient bronze idols loaded into Tata Ace van KA-04-C-1234 beneath vegetable crates."
        })

    # 5. Interstate Arms Trafficking & Rioting Syndicate (6 FIRs across Kalaburagi, Bidar, Raichur) -> Rudre Gowda network
    for i, (zone, dist, stn, lat, lon, ctype, date) in enumerate([
        ("Kalaburagi", "Kalaburagi", "KLB-01", 17.3478, 76.8366, "rioting", "2026-05-18"),
        ("Kalaburagi", "Kalaburagi", "KLB-01", 17.3510, 76.8400, "arms_act", "2026-06-05"),
        ("Bidar", "Bidar", "BDR-01", 17.9104, 77.5199, "rioting", "2026-06-22"),
        ("Bidar", "Bidar", "BDR-01", 17.9130, 77.5230, "arms_act", "2026-07-10"),
        ("Raichur", "Raichur", "RCH-01", 16.2076, 77.3550, "rioting", "2026-07-28"),
        ("Raichur", "Raichur", "RCH-01", 16.2100, 77.3580, "arms_act", "2026-08-15"),
    ]):
        syndicates.append({
            "cid": f"CR-EVID-RIOT-{i+1:02d}",
            "fir_no": f"2026-RIOT-ARM-84{i+1}",
            "zone": zone, "dist": dist, "stn": stn, "lat": lat, "lon": lon,
            "ctype": ctype, "group": ctype.upper().replace("_", " "),
            "act": "IPC 1860 U/s: 147, 148, 149, 153A Arms Act U/s: 25",
            "date": date, "stage": "charge_sheeted",
            "place": "Northeast Border Commercial Belt",
            "veh": "KA-32-AR-9900", "accused_id": "S0809",
            "mo": f"Interstate riot/arms trafficking #{i+1}. Country-made firearms and weapons supplied from border belt using Bolero KA-32-AR-9900 by Rudre Gowda gang."
        })

    # Clean old versions
    cids = [s["cid"] for s in syndicates]
    cur.execute(f"DELETE FROM FIRs WHERE fir_id IN ({','.join(['?']*len(cids))})", cids)

    csv_rows = []
    for s in syndicates:
        dt = datetime.date.fromisoformat(s["date"])
        fir_row_dict = {
            "fir_id": s["cid"], "District_Name": s["zone"], "UnitName": s["stn"],
            "FIR_YEAR": str(dt.year), "FIR_MONTH": str(dt.month), "FIR_Day": str(dt.day),
            "FIR_Stage": s["stage"], "CrimeGroup_Name": s["ctype"], "CrimeHead_Name": s["ctype"].replace("_", " ").title(),
            "Latitude": str(s["lat"]), "Longitude": str(s["lon"]), "date": s["date"],
            "lat_r": round(s["lat"], 2), "lon_r": round(s["lon"], 2), "status": s["stage"],
            "crime_type": s["ctype"], "zone": s["zone"], "station": s["stn"],
            "FIR_Type": s["fir_no"], "ActSection": s["act"], "IOName": "SPECIAL CRIME BRANCH (DSP)",
            "KGID": "500800", "Internal_IO": "OF-800", "Place_of_Offence": s["place"],
            "Distance_from_PS": "4 KM", "Beat_Name": f"{s['zone']} HIGHWAY BEAT",
            "Village_Area_Name": s["zone"], "MO_Details": s["mo"],
            "Accused_ID": s["accused_id"], "Vehicle_Reg_No": s["veh"],
            "UPI_ID": "", "IP_Address": ""
        }
        cur.execute(f"INSERT INTO FIRs ({','.join(fir_cols)}) VALUES ({fir_placeholders})",
                    [str(fir_row_dict.get(c, "")) if fir_row_dict.get(c) is not None else "" for c in fir_cols])

        csv_row = [
            s["dist"], f"{s['zone']} PS", str(dt.year), str(dt.month), "0", str(dt.day),
            "Heinous" if s["ctype"] in ("murder", "dacoity", "robbery", "rioting") else "Non Heinous", s["stage"], "Written",
            s["group"], s["ctype"].replace("_", " ").title(),
            str(s["lat"]), str(s["lon"]), f'"{s["act"]}"', "SPECIAL CRIME BRANCH (DSP)", "500800", "",
            f'"{s["place"]}"', "SOUTH FROM PS 4 KM", f"{s['zone']} HIGHWAY BEAT", s["zone"],
            "1", "0", "0", "0", "0", "1", "3", "2", "0", "2", "2" if s["stage"]=="charge_sheeted" else "0", "1" if s["stage"]=="Convicted" else "0", "1008",
            s["accused_id"], s["veh"], "", "", f'"{s["mo"]}"'
        ]
        csv_rows.append(",".join(csv_row))

    print(f"Inserted {len(syndicates)} rich non-cyber syndicate FIRs into antar.db!")

    # Supporting intelligence
    cur.execute("DELETE FROM suspects WHERE suspect_id IN ('S0801', 'S0802', 'S0803', 'S0804', 'S0805', 'S0806', 'S0807', 'S0808', 'S0809')")
    new_suspects = [
        ("S0801", "Bheema Nayak", "Bheema the Butcher", 38, "M", "PH-HWY-DAC-01", "Belagavi", "dacoit / murderer", 12, "Nayak Sr.", "Indian", "Arrested"),
        ("S0802", "Parashuram K.", "Parasu Arms", 42, "M", "PH-HWY-DAC-01", "Hubballi", "arms dealer", 8, "K. Sr.", "Indian", "Arrested"),
        ("S0803", "Karthik R.", "Speed Karthik", 24, "M", "PH-BLR-ROB-02", "Jayanagar", "stunt rider", 6, "R. Sr.", "Indian", "Convicted"),
        ("S0804", "Suresh Jain", "Jain Pawnbroker", 51, "M", "PH-BLR-ROB-02", "Banashankari", "pawnbroker / receiver", 4, "Jain Sr.", "Indian", "Arrested"),
        ("S0805", "Zaid Khan", "Zaidu", 31, "M", "PH-DRUG-CORR-01", "Indiranagar", "drug lord", 9, "Khan Sr.", "Indian", "Absconding"),
        ("S0806", "Vikramaditya", "Vicky Club", 35, "M", "PH-DRUG-CORR-01", "Mysuru-Nazarbad", "lounge owner", 5, "Aditya Sr.", "Indian", "Arrested"),
        ("S0807", "Girish Acharya", "Girish Sculptor", 48, "M", "PH-ANTIQUE-01", "Hebbal", "antique dealer", 7, "Acharya Sr.", "Indian", "Arrested"),
        ("S0808", "Manja K.", "Temple Manja", 29, "M", "PH-ANTIQUE-01", "Hubballi", "temple thief", 5, "K. Sr.", "Indian", "Arrested"),
        ("S0809", "Rudre Gowda", "Rudra Border", 41, "M", "PH-RIOT-01", "Kalaburagi", "arms supplier / rioter", 11, "Gowda Sr.", "Indian", "Arrested")
    ]
    cur.executemany("""
        INSERT INTO suspects (suspect_id, full_name, alias, age, gender, phone_hash, address_zone, occupation, prior_count, father_name, nationality, arrest_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, new_suspects)

    cur.execute("DELETE FROM relationships WHERE rel_id LIKE 'REL-EVID-%'")
    new_rels = [
        ("REL-EVID-01", "S0801", "S0802", "arms_supplier", 9, "CR-EVID-DAC-01"),
        ("REL-EVID-02", "S0803", "S0804", "receiver", 8, "CR-EVID-ROB-01"),
        ("REL-EVID-03", "S0805", "S0806", "gang_member", 7, "CR-EVID-NDP-01"),
        ("REL-EVID-04", "S0807", "S0808", "syndicate", 8, "CR-EVID-BUR-01"),
        ("REL-EVID-05", "S0809", "S0802", "associate", 7, "CR-EVID-RIOT-01")
    ]
    cur.executemany("""
        INSERT INTO relationships (rel_id, suspect_a, suspect_b, rel_type, strength, source_crime_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, new_rels)

    conn.commit()
    conn.close()

    if CSV_PATH.exists() and csv_rows:
        content = CSV_PATH.read_text(encoding="utf-8", errors="ignore")
        # Remove any old CR-EVID rows if necessary or just write fresh ones
        lines = [line for line in content.splitlines() if "CR-EVID-" not in line]
        lines.extend(csv_rows)
        with open(CSV_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Replaced/Appended {len(csv_rows)} rich non-cyber syndicate records to {CSV_PATH.name}!")

    print("\nVerifying live forecast alerts remain exactly 3 HIGH, 1 MEDIUM, 1 LOW...")
    from app.agents.forecast_agent import scan
    res = scan(session_id="verify_evidence")
    alerts = res.get("alerts", [])
    print(f"Total Active Forecast Alerts: {len(alerts)}")
    for a in alerts:
        z = a.get("z_score", 0)
        risk = "HIGH" if z >= 4 else "MEDIUM" if z >= 2.5 else "LOW"
        print(f"[{risk:<6}] {a.get('zone'):<16} | {a.get('crime_type'):<16} | z={z:<6.3f} | obs={a.get('observed')}")

if __name__ == "__main__":
    inject_evidence()
