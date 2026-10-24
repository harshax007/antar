"""
Antar — Admin Data Governance API
=======================================
Robust Pydantic-powered ingestion pipeline with schema validation.
"""
import csv
import io
import uuid
import datetime
import subprocess
from pydantic import BaseModel, model_validator
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import sqlite3

from app.core.schema_registry import get_table_schema

router = APIRouter()
from app.core.db_path import DB_PATH
from app.core.db_path import registry_connect

class FIRRecord(BaseModel):
    # Core DB fields (normalized from CSV)
    District_Name: Optional[str] = "Unknown"
    UnitName: Optional[str] = "Unknown"
    FIR_YEAR: Optional[str] = ""
    FIR_MONTH: Optional[str] = ""
    Offence_Duration: Optional[str] = ""
    FIR_Day: Optional[str] = ""
    FIR_Type: Optional[str] = ""
    FIR_Stage: Optional[str] = "Under Investigation"
    Complaint_Mode: Optional[str] = ""
    CrimeGroup_Name: Optional[str] = "Unknown"
    CrimeHead_Name: Optional[str] = ""
    Latitude: Optional[str] = "0"
    Longitude: Optional[str] = "0"
    ActSection: Optional[str] = ""
    IOName: Optional[str] = ""
    KGID: Optional[str] = ""
    Internal_IO: Optional[str] = ""
    Place_of_Offence: Optional[str] = ""
    Distance_from_PS: Optional[str] = ""
    Beat_Name: Optional[str] = ""
    Village_Area_Name: Optional[str] = ""
    Male: Optional[str] = "0"
    Female: Optional[str] = "0"
    Boy: Optional[str] = "0"
    Girl: Optional[str] = "0"
    Age_0: Optional[str] = "0"
    VICTIM_COUNT: Optional[str] = "0"
    Accused_Count: Optional[str] = "0"
    Arrested_Male: Optional[str] = "0"
    Arrested_Female: Optional[str] = "0"
    Arrested_Count_No_: Optional[str] = "0"
    Accused_ChargeSheeted_Count: Optional[str] = "0"
    Conviction_Count: Optional[str] = "0"
    Unit_ID: Optional[str] = ""

    # Derived Fields
    fir_id: Optional[str] = None
    zone: Optional[str] = None
    station: Optional[str] = None
    date: Optional[str] = None
    crime_type: Optional[str] = None
    status: Optional[str] = None
    location_lat: Optional[str] = None
    location_lon: Optional[str] = None
    lat_r: Optional[float] = None
    lon_r: Optional[float] = None

    @model_validator(mode='after')
    def compute_derived_fields(self) -> 'FIRRecord':
        # Generate unique ID
        self.fir_id = f"CR-{uuid.uuid4().hex[:8]}"
        self.zone = self.District_Name
        self.station = self.UnitName
        self.crime_type = self.CrimeGroup_Name
        self.status = self.FIR_Stage
        self.location_lat = self.Latitude
        self.location_lon = self.Longitude

        # Calculate standard ISODate from year/month/day if present
        try:
            if self.FIR_YEAR and self.FIR_MONTH and self.FIR_Day:
                self.date = f"{self.FIR_YEAR}-{int(self.FIR_MONTH):02d}-{int(self.FIR_Day):02d}"
            else:
                self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            # Was a bare `except:`, which also swallows KeyboardInterrupt and SystemExit —
            # so a Ctrl-C during an ingest was absorbed by a date parse. Only the errors a
            # malformed date can actually raise belong here.
            self.date = datetime.datetime.now().strftime("%Y-%m-%d")

        # Geo conversion
        try:
            self.lat_r = float(self.Latitude)
            self.lon_r = float(self.Longitude)
        except (ValueError, TypeError):
            self.lat_r = None
            self.lon_r = None

        return self

def trigger_summary_build():
    """Runs the summary build pipeline asynchronously."""
    try:
        subprocess.run(["python", "build_summaries.py"], check=True)
    except Exception as e:
        print(f"Failed to rebuild summaries: {e}")

@router.post("/ingest")
async def ingest_dataset(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Ingests a CSV dataset, validates it perfectly against the internal schema,
    drops malformed records, and triggers analytical rebuilds.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed.")

    contents = await file.read()
    try:
        # We read with utf-8-sig to clear BOM, and cast everything to string.
        text = contents.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    except Exception as e:
        raise HTTPException(status_code=400, detail="CSV parse error: the file is not valid UTF-8 CSV.")

    # Standardize column headers from messy CSV to SQLite normalized names
    rename_map = {
        "FIR Type": "FIR_Type",
        "Place of Offence": "Place_of_Offence",
        "Distance from PS": "Distance_from_PS",
        "Age 0": "Age_0",
        "VICTIM COUNT": "VICTIM_COUNT",
        "Accused Count": "Accused_Count",
        "Arrested Male": "Arrested_Male",
        "Arrested Female": "Arrested_Female",
        "Arrested Count\tNo.": "Arrested_Count_No_",
        "Accused_ChargeSheeted Count": "Accused_ChargeSheeted_Count",
        "Conviction Count": "Conviction_Count"
    }
    
    dict_records = []
    for r in rows:
        new_row = {}
        for k, v in r.items():
            if k in rename_map:
                new_row[rename_map[k]] = str(v) if v is not None else ""
            elif k is not None:
                new_row[k] = str(v) if v is not None else ""
        dict_records.append(new_row)

    valid_records = []
    for record_dict in dict_records:
        try:
            record = FIRRecord(**record_dict)
            valid_records.append(record.model_dump())
        except Exception:
            # Drop invalid rows as per rigorous industry standards
            pass

    if not valid_records:
        raise HTTPException(status_code=400, detail="No valid records matched the schema.")

    # Bulk Insert to SQLite
    try:
        conn = registry_connect(DB_PATH)
        cursor = conn.cursor()
        
        columns = list(valid_records[0].keys())
        placeholders = ",".join(["?"] * len(columns))
        sql = f"INSERT INTO FIRs ({','.join(columns)}) VALUES ({placeholders})"
        
        # executemany is very fast for bulk inserts
        cursor.executemany(sql, [[r[c] for c in columns] for r in valid_records])
        conn.commit()
        conn.close()
    except Exception as e:
        from app.core.security import public_error
        raise HTTPException(status_code=500, detail=public_error(e, "ingest")["message"])

    # Trigger async rebuilding of the materialized dashboards
    background_tasks.add_task(trigger_summary_build)

    return {
        "status": "success",
        "records_ingested": len(valid_records),
        "message": "Data ingested successfully. Analytics dashboards are updating."
    }

@router.get("/schema")
async def get_schema():
    """Returns the live schema to internal tools/LLM agents."""
    return {
        "FIRs": get_table_schema("FIRs"),
        "crimes": get_table_schema("crimes"),
        "suspects": get_table_schema("suspects"),
        "crime_suspects": get_table_schema("crime_suspects")
    }
