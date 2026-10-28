"""
tests/test_fir_clean.py — Unit tests for app.services.fir_clean (Phase L1.1).
"""

from __future__ import annotations

import pytest
from app.services.fir_clean import (
    canonical_stage,
    parse_act_section,
    clean_coords,
    signature,
)


def test_canonical_stage_standard():
    assert canonical_stage("Pending Trial") == ("Pending Trial", 1)
    assert canonical_stage("pending trial") == ("Pending Trial", 1)
    assert canonical_stage("Convicted") == ("Convicted", 11)
    assert canonical_stage("Dis/Acq") == ("Dis/Acq", 4)
    assert canonical_stage("Dis / Acq") == ("Dis/Acq", 4)
    assert canonical_stage("BoundOver") == ("BoundOver", 226)
    assert canonical_stage("Bound Over") == ("BoundOver", 226)
    assert canonical_stage("Under Investigation") == ("Under Investigation", 5)
    assert canonical_stage("UI") == ("Under Investigation", 5)
    assert canonical_stage("U.I") == ("Under Investigation", 5)
    assert canonical_stage("Un Traced") == ("Un Traced", 23)
    assert canonical_stage("Untraced") == ("Un Traced", 23)


def test_canonical_stage_transfers():
    assert canonical_stage("Transfered :UI( CID)") == ("Transferred - Under Investigation", 7)
    assert canonical_stage("Transfered :UI( CCB Bengaluru City Police)") == (
        "Transferred - Under Investigation",
        7,
    )
    assert canonical_stage("Transferred - Under Investigation") == (
        "Transferred - Under Investigation",
        7,
    )


def test_parse_act_section_pocso_sample():
    # From CSV head row 0:
    raw = (
        "PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012 U/s: 12 "
        "IPC 1860 U/s: 306,363 "
        "PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012 U/s: 18 "
    )
    res = parse_act_section(raw)
    assert len(res) == 4

    # Group 0: POCSO, sec 12
    assert res[0]["order"] == 0
    assert "CHILDREN" in res[0]["act_raw"]
    assert res[0]["section"] == "12"

    # Group 1: IPC 1860, secs 306, 363
    assert res[1]["order"] == 1
    assert res[1]["act_raw"] == "IPC 1860"
    assert res[1]["section"] == "306"

    assert res[2]["order"] == 1
    assert res[2]["act_raw"] == "IPC 1860"
    assert res[2]["section"] == "363"

    # Group 2: POCSO again, sec 18
    assert res[3]["order"] == 2
    assert "CHILDREN" in res[3]["act_raw"]
    assert res[3]["section"] == "18"


def test_parse_act_section_subclauses():
    raw = "IPC 1860 U/s: 304(A),279 KARNATAKA POLICE ACT 1963 U/s: 78(3)"
    res = parse_act_section(raw)
    sections = [r["section"] for r in res]
    assert "304(A)" in sections
    assert "279" in sections
    assert "78(3)" in sections


def test_clean_coords():
    # Regular valid Karnataka coords
    lat, lon, reason = clean_coords(12.9716, 77.5946)
    assert reason == "ok"
    assert lat == 12.9716
    assert lon == 77.5946

    # Swapped coords (lon in lat spot, lat in lon spot)
    lat, lon, reason = clean_coords(77.5946, 12.9716)
    assert reason == "swapped"
    assert lat == 12.9716
    assert lon == 77.5946

    # Outside bounds
    _, _, reason = clean_coords(28.6139, 77.2090)  # Delhi
    assert reason == "outside"

    # Missing / NaN / 0
    _, _, reason = clean_coords(None, None)
    assert reason == "missing"
    _, _, reason = clean_coords("nan", "nan")
    assert reason == "missing"
    _, _, reason = clean_coords(0.0, 0.0)
    assert reason == "missing"


def test_signature_deterministic():
    row1 = {
        "District_Name": "Bagalkot",
        "UnitName": "Amengad PS",
        "FIR_YEAR": "2016",
        "FIR_MONTH": "1",
        "FIR_Day": "12",
        "FIR_Type": "Non Heinous",
        "CrimeGroup_Name": "KARNATAKA POLICE ACT 1963",
        "CrimeHead_Name": "Gambling - Matka (78 Class C)",
        "KGID": "1270757",
        "Beat_Name": "RURAL BEAT NO 6",
        "Village_Area_Name": "SULEBAVI",
        "Accused_Count": "1",
        "Place_of_Offence": "RAKKASAGI VILLAEG BUS STAND, RAKKASAGI VILLAEG BUS STAND",
    }
    # Variation in spacing / case / column naming
    row2 = {
        "District_Name": " bagalkot ",
        "UnitName": "Amengad PS",
        "FIR_YEAR": 2016,
        "FIR_MONTH": 1,
        "FIR_Day": "012",
        "FIR Type": "non heinous",
        "CrimeGroup_Name": "KARNATAKA POLICE ACT 1963",
        "CrimeHead_Name": "Gambling - Matka (78 Class C)",
        "KGID": "1270757",
        "Beat_Name": "RURAL BEAT NO 6",
        "Village_Area_Name": "SULEBAVI",
        "Accused Count": "1.0",
        "Place of Offence": "RAKKASAGI VILLAEG BUS STAND, RAKKASAGI VILLAEG BUS STAND",
    }
    sig1 = signature(row1)
    sig2 = signature(row2)
    assert sig1 == sig2
    assert len(sig1) == 40
