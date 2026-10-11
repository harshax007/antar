"""
Antar — Second Brain Cross-Case Retrieval (WOW 2)
Given a suspect, surface links to OTHER cases that were never formally connected
(e.g. alias 'Yellappa' matches a Mysuru case 8 months ago).

Design (robust by construction):
  • PRIMARY signal = DATA overlap (deterministic, demo-guaranteed):
      shared phone_hash + shared contacts across different stations/cities.
  • ENRICHMENT = semantic recall from the Second Brain embedding index (the planted
      investigation summaries), added when the index is seeded. Adds narrative color,
      never required for the link to appear.

This is why WOW 2 cannot silently fail: it rests on the planted relationships, not on
embedding luck. The brain summary just makes the banner richer.
"""

from __future__ import annotations

from datetime import datetime

from app.services.zcql_local import _world


def _neighbors(suspect_id: str, world: dict) -> set[str]:
    """Suspect ids directly related to this one (relationship edges)."""
    out = set()
    for r in world["relationships"]:
        if r["suspect_a"] == suspect_id:
            out.add(r["suspect_b"])
        elif r["suspect_b"] == suspect_id:
            out.add(r["suspect_a"])
    return out


def _crimes_of(suspect_id: str, world: dict) -> list[dict]:
    cids = {cs["crime_id"] for cs in world["crime_suspects"] if cs["suspect_id"] == suspect_id}
    return [c for c in world["crimes"] if c["crime_id"] in cids]


def _months_ago(iso_dt: str) -> int:
    try:
        d = datetime.fromisoformat(iso_dt)
        now = datetime.now()
        return max(0, (now.year - d.year) * 12 + (now.month - d.month))
    except Exception:
        return 0


def _city(zone: str) -> str:
    if zone and zone.startswith("Mysuru"):
        return "Mysuru"
    return "Bengaluru" if zone in (
        "Rajajinagar", "Gandhinagar", "Jayanagar", "Malleshwaram", "Indiranagar",
        "Whitefield", "Yeshwanthpur", "Banashankari", "KR Puram", "Hebbal") else (zone or "")


def find_cross_case_links(seed_id: str, world: dict | None = None) -> dict:
    """
    Returns {"links": [...], "banner": str|None}.
    A link = another suspect tied to the seed by a hidden signal (shared phone +
    common contacts), typically in a different case/city.
    """
    world = world or _world()
    suspects = {s["suspect_id"]: s for s in world["suspects"]}
    seed = suspects.get(seed_id)
    if not seed:
        return {"links": [], "banner": None}

    seed_neighbors = _neighbors(seed_id, world)
    seed_city = _city(seed["address_zone"])
    links = []

    for s in world["suspects"]:
        sid = s["suspect_id"]
        if sid == seed_id:
            continue
        shares_phone = seed.get("phone_hash") and s.get("phone_hash") == seed["phone_hash"]
        if not shares_phone:
            continue
        common = sorted(seed_neighbors & _neighbors(sid, world))
        crimes = _crimes_of(sid, world)
        anchor = min(crimes, key=lambda c: c["occurred_at"]) if crimes else None
        links.append({
            "suspect_id": sid,
            "full_name": s.get("full_name"),
            "alias": s.get("alias"),
            "zone": s.get("address_zone"),
            "city": _city(s.get("address_zone")),
            "overlap_type": "shared_phone",
            "shared_contacts": common,
            "shared_contact_count": len(common),
            "anchor_fir": anchor["fir_number"] if anchor else None,
            "anchor_zone": anchor["zone"] if anchor else None,
            "months_ago": _months_ago(anchor["occurred_at"]) if anchor else None,
            "cross_city": _city(s.get("address_zone")) != seed_city,
            "score": 0.95,
        })

    # strongest first: cross-city + most shared contacts
    links.sort(key=lambda l: (l["cross_city"], l["shared_contact_count"]), reverse=True)
    banner = _build_banner(seed, links, world)
    return {"links": links, "banner": banner}


def _build_banner(seed: dict, links: list[dict], world: dict) -> str | None:
    if not links:
        return None
    top = links[0]
    who = f"alias '{seed['alias']}'" if seed.get("alias") else seed.get("full_name", "this suspect")
    where = top.get("anchor_zone") or top.get("zone") or "another district"
    fir = f" (FIR {top['anchor_fir']})" if top.get("anchor_fir") else ""
    months = f" ~{top['months_ago']} months ago" if top.get("months_ago") else ""
    n = top["shared_contact_count"]
    contacts = f", {n} common contact{'s' if n != 1 else ''}" if n else ""
    return (f"Second Brain: {who} links {seed.get('full_name')} to a case in {where}{fir}"
            f"{months} — shared phone number{contacts}, never formally connected.")


async def decompose_query(query_text: str, use_llm: bool = False) -> list[str]:
    """Split compound or multi-intent questions into discrete analytical sub-queries.
    If use_llm is True, performs advanced Multi-Query RAG expansion to boost recall.
    """
    import re
    clean = (query_text or "").strip()
    if not clean or len(clean) < 15:
        return [clean] if clean else []
        
    if use_llm:
        from app.services.quickml import quickml_generate
        import json
        sys_prompt = "You are an AI query expander. Rewrite the user's crime query into 3 distinct, highly targeted search variations (synonyms, different angles) to maximize vector database recall. Output ONLY a valid JSON array of 3 strings."
        try:
            raw = await quickml_generate(system=sys_prompt, user=clean, json_mode=True, max_tokens=150)
            cleaned = raw.strip().strip("```json").strip("```").strip()
            variants = json.loads(cleaned)
            if isinstance(variants, list) and variants:
                return variants[:3]
        except Exception as e:
            print(f"LLM decompose failed: {e}")
            
    # Fallback to deterministic regex split
    splits = re.split(r"(?i)\b(?:and\s+also|and\s+check|as\s+well\s+as|then\s+find|vs\.?|versus)\b|\?|\. |; ", clean)
    sub = [s.strip() for s in splits if len(s.strip()) > 8]
    return sub if sub else [clean]


_OVERSAMPLE = 4    # fetch k×4 from HNSW+BM25; rerank then MMR narrow to k


def semantic_recall(
    query_text: str,
    k: int = 3,
    rerank: bool = True,
    mmr_lambda: float = 0.7,
    terms: list[str] | None = None,
    use_hybrid: bool = True,
    expand_with_llm: bool = False,
) -> list[dict]:
    """Three-stage Brain recall: Decompose/Hybrid (HNSW+BM25) → cross-encoder rerank → MMR diversification.

    Stage 1 — Multi-query hybrid search: splits compound query, fetches k×_OVERSAMPLE
               candidates fused by Reciprocal Rank Fusion (rank-based, alpha=0.7
               semantic / 0.3 lexical). Rank fusion — not the previous max-normalised
               score blend — is what lets an exact identifier (ACC-id, FIR no., vehicle
               reg, UPI) win: BM25 puts it at rank 1, and RRF rewards the rank instead
               of a raw score whose scale is incomparable to a cosine.
    Stage 2 — Cross-encoder rerank: jointly encode (query, doc) pairs for
               precision; narrow to k×2. Falls back to hybrid score if offline.
    Stage 3 — MMR: greedily select k results balancing relevance vs diversity
               (λ=mmr_lambda). No-op when candidates ≤ k.
    """
    try:
        from app.second_brain.index import brain_index
        from app.second_brain.embedder import embed_query, embed_query_with_terms
        from app.second_brain.reranker import reranker, mmr
        import asyncio

        if brain_index.size == 0:
            return []

        # Run async decompose_query safely inside the synchronous thread pool
        try:
            loop = asyncio.get_running_loop()
            sub_queries = [query_text] # fallback if already in an event loop without nesting capability
        except RuntimeError:
            # Query expansion by the language model is opt-in. It used to run on every
            # call, and the chat stream makes this call on every question: each answer
            # waited 16-19 s for three rewordings of the question before it searched a
            # curated index of a handful of rows. The answer itself had been ready in
            # 0.1 s, and officers stopped the turn before it arrived.
            sub_queries = asyncio.run(decompose_query(query_text, use_llm=use_hybrid and expand_with_llm))

        merged_candidates = {}

        for sq in sub_queries:
            # Both branches must return an index-space (768) query vector.
            qvec = embed_query_with_terms(sq, terms) if terms else embed_query(sq)

            fetch_k = min(brain_index.size, k * _OVERSAMPLE)
            if use_hybrid and hasattr(brain_index, "hybrid_search"):
                candidates = brain_index.hybrid_search(qvec, sq, k=fetch_k, alpha=0.7)
            else:
                candidates = brain_index.cosine_topk(qvec, k=fetch_k)

            for c in candidates:
                rid = c.get("row_id")
                if rid not in merged_candidates or c.get("score", 0) > merged_candidates[rid].get("score", 0):
                    merged_candidates[rid] = c

        candidates = sorted(merged_candidates.values(), key=lambda x: x.get("score", 0), reverse=True)
        if not candidates:
            return []

        # Use the primary query vector for MMR/Rerank
        # MMR compares this against brain_index._matrix, so it must be index-space too.
        primary_vec = embed_query_with_terms(query_text, terms) if terms else embed_query(query_text)

        # Stage 2: Cross-encoder rerank — narrow to k*2
        if rerank and reranker.available:
            candidates = reranker.rerank(
                query_text, candidates,
                top_n=min(len(candidates), k * 2),
            )

        # -- Phase 3: Attention (Corroboration) Blending --
        # Blend the cross-encoder relevance score with the static cluster attention_score
        for c in candidates:
            base_score = c.get("score", 0.0)
            attention_score = float(c.get("attention_score", 0.0))
            
            # Weighted blend: 80% query relevance, 20% global corroboration centrality
            c["score"] = 0.8 * base_score + 0.2 * attention_score

        # Stage 3: MMR — select k diverse results
        if len(candidates) > k and mmr_lambda < 1.0:
            candidates = mmr(
                primary_vec, candidates,
                brain_index._matrix, k, mmr_lambda,
            )
        else:
            candidates = candidates[:k]

        # Strip internal bookkeeping field before returning to callers
        for c in candidates:
            c.pop("_matrix_idx", None)
            c.pop("rerank_score", None)

        return candidates
    except Exception as e:
        import traceback
        print(f"  ⚠️  semantic_recall error: {e}")
        traceback.print_exc()
        return []


# ── FIR corpus similarity (final_backend.md §6 P1-2) ──────────────────────────────────

def corpus_recall(query_text: str, k: int = 10, *, min_score: float = 0.25,
                  district: str | None = None, crime_group: str | None = None) -> list[dict]:
    """Find FIRs whose recorded circumstances resemble `query_text`.

    This is the case-similarity tier: one vector per FIR, held on disk by
    `app.second_brain.vec_store` and scanned in chunks, so recall over a hundred thousand
    cases costs a few MB of working set rather than growing the in-memory index.

    Separate from `semantic_recall()` on purpose. That one searches the CURATED tier —
    investigation summaries and consolidated learnings, which carry confidence and
    verification state. This one searches the RECORD: what the FIR itself says happened
    and where. An officer asking "have we seen this MO before" wants the record.

    Returns hits ordered by cosine, each with the FIR text that matched and its metadata,
    so the answer can cite the case rather than assert a resemblance.
    """
    from app.second_brain import embedder, vec_store

    if not (query_text or "").strip():
        return []
    try:
        if embedder._model is None:
            embedder.load_embedder()
        if embedder._model is None:
            return []
        # Document space, matching how the corpus was embedded by
        # scripts/build_brain_index.py — a query vector from the 768-dim index space
        # would not be comparable to these 384-dim rows.
        qvec = embedder.embed([query_text])[0]
    except Exception as e:                       # recall is an enhancement, never a 500
        print(f"  ⚠️  corpus recall unavailable: {e}")
        return []

    # Over-fetch before filtering so a district/crime filter cannot empty the result.
    fetch = k * (6 if (district or crime_group) else 2)
    hits = vec_store.search(qvec, k=max(fetch, k), kind="fir", min_score=min_score)
    if district:
        d = district.strip().lower()
        hits = [h for h in hits if d in str(h["meta"].get("district", "")).lower()]
    if crime_group:
        g = crime_group.strip().lower()
        hits = [h for h in hits if g in str(h["meta"].get("crime_group", "")).lower()]

    # The registry holds genuinely duplicated circumstances (same place, same MO text,
    # different FIR). Showing the same line three times reads as a broken result and
    # wastes the officer's shortlist, so keep the best-scoring instance of each text.
    seen: set[str] = set()
    unique = []
    for h in hits:
        key = " ".join(h["summary_text"].split()).lower()[:160]
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)
    return unique[:k]
