"""
Antar — Multimodal Forensic OCR & ML Victim Identification API Router
Provides REST endpoints for scanning FIR evidence documents and performing ML victim linkage.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.services.forensic_ocr import analyze_forensic_evidence, FORENSIC_SAMPLE_PRESETS
from app.core.auth_middleware import require_role
from app.core.rate_limiter import rate_limit
from app.core.security import public_error

router = APIRouter(prefix="/api/forensic", tags=["forensic"])

# A scanned page at evidence resolution is ~2-6 MB of base64; 10 MB leaves headroom
# without letting one request pin the vision endpoint or the process's memory.
_MAX_IMAGE_B64 = 10 * 1024 * 1024


class ForensicAnalyzeRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, max_length=_MAX_IMAGE_B64)
    preset_key: Optional[str] = Field(default="SAMPLE_1", max_length=40)
    custom_notes: Optional[str] = Field(default="", max_length=2000)
    historical_records: Optional[List[Dict[str, Any]]] = Field(default=None, max_length=500)


@router.get("/presets")
async def get_forensic_presets():
    """Returns available 1-click forensic evidence samples for instant testing."""
    presets_summary = []
    for k, v in FORENSIC_SAMPLE_PRESETS.items():
        presets_summary.append({
            "preset_key": k,
            "title": v.get("title"),
            "document_type": v.get("document_type"),
            "district": v.get("district"),
            "crime_type": v.get("crime_type")
        })
    return {"status": "SUCCESS", "presets": presets_summary}


@router.post("/analyze", dependencies=[Depends(require_role("Inspector")),
                                       Depends(rate_limit(20, 0.2))])
async def analyze_evidence(req: ForensicAnalyzeRequest):
    """
    Executes Multimodal Forensic OCR (VL-Qwen3.6-35B-A3B) & ML Victim Linkage.
    """
    try:
        result = await analyze_forensic_evidence(
            image_base64=req.image_base64,
            preset_key=req.preset_key,
            custom_notes=req.custom_notes or "",
            historical_recs=req.historical_records
        )
        return result
    except Exception as e:
        # Never str(e): a vision-endpoint failure carries the upstream body and URL.
        raise HTTPException(status_code=500, detail=public_error(e, "vision")["message"])
