"""
Antar — Upload API (Phase 8)
=================================
Endpoints for data-agnostic CSV ingestion.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.ingestion import map_and_ingest_csv, MAX_CSV_BYTES
from app.core.rate_limiter import rate_limit
from app.core.auth_middleware import require_role

router = APIRouter()

# Writing into the FIR registry changes what every officer's answers are built from —
# the RAG "corpus poisoning" risk. Admin only, and slower than chat.
_WRITE = [Depends(require_role("Admin")), Depends(rate_limit(10, 0.05))]


@router.post("", dependencies=_WRITE)
@router.post("/", dependencies=_WRITE)
async def upload_csv(file: UploadFile = File(...)):
    """
    Accepts a CSV file, heuristically maps its columns to the canonical schema,
    and inserts the records into the active data store.
    """
    if not (file.filename or "").lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Read at most one byte past the limit: enough to reject, never the whole stream.
    contents = await file.read(MAX_CSV_BYTES + 1)
    
    result = map_and_ingest_csv(contents)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result
