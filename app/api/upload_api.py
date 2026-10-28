"""
Antar — Upload API (Phase 8)
=================================
Endpoints for data-agnostic CSV ingestion, and the Admin · Data flow for adding
FIRs in the KSP export format: check the file, add it, see past uploads, undo one.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.ingestion import map_and_ingest_csv, MAX_CSV_BYTES
from app.services import fir_upload
from app.core.rate_limiter import rate_limit
from app.core.auth_middleware import require_role, current_identity

router = APIRouter()

# Writing into the FIR registry changes what every officer's answers are built from —
# the RAG "corpus poisoning" risk. Admin only, and slower than chat.
_WRITE = [Depends(require_role("Admin")), Depends(rate_limit(10, 0.05))]
_READ = [Depends(require_role("Admin"))]


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


@router.get("/template", dependencies=_READ)
async def upload_template():
    """The KSP FIR export columns, with two sample rows."""
    return Response(fir_upload.template(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="antar_fir_upload_template.csv"'})


@router.post("/preview", dependencies=_WRITE)
async def upload_preview(request: Request, file: UploadFile = File(...)):
    """Check every row; nothing is written. Returns a preview_id valid for 15 minutes."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    contents = await file.read(fir_upload.MAX_BYTES + 1)
    try:
        return fir_upload.preview(contents, file.filename or "upload.csv", current_identity(request).officer)
    except fir_upload.UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))


class CommitBody(BaseModel):
    preview_id: str


@router.post("/commit", dependencies=_WRITE)
async def upload_commit(body: CommitBody, request: Request):
    ident = current_identity(request)
    try:
        return fir_upload.commit(body.preview_id, ident.officer, ident.role)
    except fir_upload.UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", dependencies=_READ)
async def upload_history(limit: int = 50):
    return {"uploads": fir_upload.history(max(1, min(limit, 200)))}


class UndoBody(BaseModel):
    reason: str


@router.post("/{batch_id}/undo", dependencies=_WRITE)
async def upload_undo(batch_id: str, body: UndoBody, request: Request):
    ident = current_identity(request)
    try:
        return fir_upload.undo(batch_id, ident.officer, ident.role, body.reason)
    except fir_upload.UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
