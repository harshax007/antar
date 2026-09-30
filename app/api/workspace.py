"""
Antar — Expert Workspace API (/api/workspace)
==============================================
Provides unified access to completed background investigations, intelligence
products, dossiers, annotations, and archived items for the frontend workspace tab.
"""

from __future__ import annotations
import time
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

# In-memory annotations & bookmarks specific to workspace items (backed by memory.py for persistence)
_WORKSPACE_NOTES: dict[str, list[dict[str, Any]]] = {}


class NoteRequest(BaseModel):
    item_id: str
    text: str = Field(min_length=1, max_length=1000)
    officer_id: str = "OF-1001"


@router.get("")
@router.get("/")
async def list_workspace_items(request: Request) -> dict[str, Any]:
    """Gather all completed jobs, dossiers, and compiled intelligence products for the workspace."""
    from app.api.jobs import list_jobs_sync
    from app.services.product_store import list_products
    from app.core.memory import get_officer_memory
    
    from app.core.auth_middleware import current_identity
    officer_id = current_identity(request).officer
    mem = get_officer_memory(officer_id)
    
    # 1. Fetch completed and running jobs from jobs.py
    raw_jobs = list_jobs_sync().get("jobs", [])
    workspace_items = []
    
    for j in raw_jobs:
        workspace_items.append({
            "id": j["job_id"],
            "type": "job",
            "subtype": j.get("type"),
            "title": f"Investigation: {j.get('target') or j.get('type')}",
            "status": j.get("status"),
            "summary": j.get("summary") or f"Status: {j.get('status')}",
            "result": j.get("result"),
            "created_at": j.get("created_at"),
            "finished_at": j.get("finished_at"),
            "notes": _WORKSPACE_NOTES.get(j["job_id"], [])
        })
        
    # 2. Fetch intelligence products from product_store
    try:
        from app.services.product_store import get_product
        # list_products() returns KEYS, not payloads — calling .get() on each key string
        # raised on every poll ("'str' object has no attribute 'get'"), so the workspace
        # never showed a single product.
        for key in list_products():
            p = get_product(key)
            if not isinstance(p, dict) or not (p.get("title") or p.get("kind")):
                continue   # internal caches (unsub:*, session_kul:*) are not workspace dossiers
            pid = str(p.get("id") or p.get("product_id") or key)
            workspace_items.append({
                "id": pid,
                "type": "product",
                "subtype": p.get("kind", "dossier"),
                "title": p.get("title") or f"Intelligence Product: {pid}",
                "status": "done",
                "summary": p.get("summary") or "Precompiled intelligence board/dossier.",
                "result": p.get("data") or p,
                "created_at": p.get("updated_at") or int(time.time()),
                "finished_at": p.get("updated_at") or int(time.time()),
                "notes": _WORKSPACE_NOTES.get(pid, [])
            })
    except Exception as e:
        print(f"Error fetching products for workspace: {e}")
        
    # Sort descending by creation timestamp
    workspace_items.sort(key=lambda x: x.get("created_at", 0) or 0, reverse=True)
    
    return {
        "items": workspace_items[:50],
        "bookmarks": mem.get("bookmarks", []),
        "conclusions": mem.get("conclusions", []),
        "officer": mem
    }


@router.get("/{item_id}")
async def get_workspace_item(item_id: str) -> dict[str, Any]:
    """Get full payload, notes, and evidence trail for a specific workspace item."""
    from app.api.jobs import get_job_sync
    from app.services.product_store import get_product
    
    if item_id.startswith("job-"):
        job = get_job_sync(item_id)
        if not job:
            raise HTTPException(status_code=404, detail="Workspace job item not found")
        return {
            "id": job["job_id"],
            "type": "job",
            "subtype": job.get("type"),
            "title": f"Investigation: {job.get('target') or job.get('type')}",
            "status": job.get("status"),
            "summary": job.get("summary"),
            "result": job.get("result"),
            "created_at": job.get("created_at"),
            "notes": _WORKSPACE_NOTES.get(item_id, [])
        }
    else:
        prod = get_product(item_id)
        if not prod:
            raise HTTPException(status_code=404, detail="Workspace product item not found")
        return {
            "id": item_id,
            "type": "product",
            "subtype": prod.get("kind", "dossier"),
            "title": prod.get("title") or f"Product: {item_id}",
            "status": "done",
            "summary": prod.get("summary"),
            "result": prod.get("data") or prod,
            "created_at": prod.get("updated_at") or int(time.time()),
            "notes": _WORKSPACE_NOTES.get(item_id, [])
        }


@router.post("/{item_id}/note")
async def add_workspace_note(item_id: str, req: NoteRequest) -> dict[str, Any]:
    """Add an analytical annotation or comment to a workspace item."""
    notes = _WORKSPACE_NOTES.setdefault(item_id, [])
    note_entry = {
        "note_id": f"note-{int(time.time()*1000)}",
        "officer_id": req.officer_id,
        "text": req.text.strip(),
        "created_at": int(time.time())
    }
    notes.append(note_entry)
    
    # Also record this conclusion into officer long-term memory
    from app.core.memory import add_officer_conclusion
    add_officer_conclusion(req.officer_id, f"Workspace Note [{item_id}]: {req.text.strip()[:100]}")
    
    return {"status": "ok", "notes": notes}
