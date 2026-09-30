"""
Antar — Adversarial Audit API (/api/adversarial-audit)
===================================================
Adversarial review of inferred hypotheses. Read-only: it changes no case state and
promotes nothing — it only argues against what another agent proposed.

  GET  /api/adversarial-audit/anchor/{anchor}      challenge a whole research dossier
  POST /api/adversarial-audit/hypothesis           challenge one hypothesis object
  GET  /api/adversarial-audit/hypothesis/{hyp_id}  challenge a stored hypothesis
  GET  /api/adversarial-audit/base-rates           population base rates (the raw evidence)
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents import adversarial_audit as da

router = APIRouter()


class HypothesisPayload(BaseModel):
    id: str = Field(default="HYP-ADHOC")
    kind: str = Field(default="association")
    claim: str = ""
    score: float | None = None
    subject_ids: list[str] = Field(default_factory=list, max_length=2)
    signals: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/anchor/{anchor}")
async def challenge_anchor(anchor: str, limit: int = 10) -> dict:
    """Build the research dossier for `anchor`, then argue against every hypothesis in it."""
    if not (anchor or "").strip():
        raise HTTPException(status_code=400, detail="anchor is required")
    # run_research + the population index are synchronous CPU work over ~2.4k suspects;
    # off the event loop so a review never stalls concurrent chat turns.
    return await asyncio.to_thread(da.run, anchor.strip(), limit=max(1, min(limit, 25)))


@router.post("/hypothesis")
async def challenge_one(payload: HypothesisPayload) -> dict:
    """Challenge a hypothesis supplied by the caller (the Brain screen posts one here)."""
    if len(payload.subject_ids) != 2:
        raise HTTPException(status_code=400, detail="subject_ids must name exactly two suspects")
    return await asyncio.to_thread(da.challenge, payload.model_dump())


@router.get("/hypothesis/{hypothesis_id}")
async def challenge_stored(hypothesis_id: str) -> dict:
    """Challenge a hypothesis already held in the product store."""
    from app.services.product_store import get_product

    hyp = get_product(f"hypothesis:{hypothesis_id}")
    if not hyp:
        raise HTTPException(status_code=404, detail=f"no stored hypothesis '{hypothesis_id}'")
    return await asyncio.to_thread(da.challenge, hyp)


@router.get("/base-rates")
async def base_rates() -> dict:
    """The population statistics every verdict is derived from.

    Exposed deliberately: an adversarial check that cannot be audited is just another
    opaque score. Every likelihood ratio in a challenge is reproducible from these counts.
    """
    def _collect() -> dict:
        idx = da._index_cached()
        top = lambda d, k=8: sorted(                    # noqa: E731 — local formatting helper
            ({"value": v, "count": n, "share": round(n / idx.N, 4)} for v, n in d.items()),
            key=lambda x: -x["count"])[:k]
        return {
            "population": idx.N,
            "mean_co_accused_per_suspect": round(idx.mean_co_accused, 3),
            "pair_collision_rates": {
                k: {"p": round(v, 9),
                    "interpretation": f"{v:.2%} of random suspect pairs share this attribute"}
                for k, v in sorted(idx.collision.items(), key=lambda x: -x[1])
            },
            "top_values": {
                "address_zone": top(idx.zone_counts),
                "mo_or_occupation": top(idx.mo_counts),
            },
            "note": ("A signal is only evidence to the extent that few pairs share it. "
                     "Attributes near the top of this list are population-typical and "
                     "carry no inferential load."),
        }

    return await asyncio.to_thread(_collect)
