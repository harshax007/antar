"""
Antar — Second Brain Embedder
Singleton BGE-small model. Loaded once at startup (Gate G1 tests this).

Model: BAAI/bge-small-en-v1.5 (384-dim, ~33MB)
  - Top MTEB retrieval scores for its size class (outperforms all-MiniLM-L6-v2
    on MS-MARCO, BeIR, MTEB Retrieval avg by ~3-4 points).
  - Same 384-dim output → zero structural changes needed elsewhere.
  - BGE models use CLS pooling + L2 normalisation (normalize_embeddings=True).
  - Asymmetric retrieval: queries get the 'Represent this sentence for
    searching relevant passages: ' prefix; documents are embedded as-is.
    This matches the official bge-small fine-tuning convention.
"""

import os

# Second Brain runs OFFLINE-FIRST: load the embedder from the local Hugging Face
# cache and never block startup on huggingface.co HEAD checks (which otherwise
# retry 5× per file when there's no network, hanging the boot for ~minutes).
# Set ANTAR_BRAIN_ONLINE=1 to permit a one-time online download on a fresh machine.
# These env vars MUST be set before importing sentence_transformers / huggingface_hub.
_ALLOW_ONLINE = os.getenv("ANTAR_BRAIN_ONLINE") == "1"
if not _ALLOW_ONLINE:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# sentence_transformers is imported LAZILY, inside load_embedder(). Importing it at module
# scope pulls in torch + transformers, which costs several seconds and a few hundred MB of
# RSS — and it happened during `import main`, i.e. BEFORE uvicorn could bind its port. On a
# Catalyst cold start that time is dead time: the container is up but not yet accepting
# connections, so the platform's health probe and the first user request both queue behind
# a model framework that only the Second Brain needs. Deferring it lets the port open
# immediately and moves the cost into background_warmup(), where main.py already puts the
# rest of the heavy initialisation.
SentenceTransformer = None
_st_import_failed = False

try:
    import numpy as np
except ImportError:
    np = None
from app.core.settings import settings


def _load_sentence_transformers():
    """Import sentence_transformers on first use. Returns the class, or None if absent."""
    global SentenceTransformer, _st_import_failed
    if SentenceTransformer is not None or _st_import_failed:
        return SentenceTransformer
    try:
        from sentence_transformers import SentenceTransformer as _ST
        SentenceTransformer = _ST
    except ImportError:
        _st_import_failed = True
    return SentenceTransformer

# BGE asymmetric retrieval prefix (applied to QUERIES only, not documents).
# ponytail: one constant, referenced in embed_query() only.
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


def _load_onnx_embedder():
    """The ONNX runtime path: same weights, no torch (final_backend.md §4 step 6).

    Returns a loaded encoder, or None to fall back to sentence-transformers. Selected by
    ANTAR_BRAIN_BACKEND: "auto" (default) uses ONNX when an export for the configured
    model exists, "onnx" demands it, "torch" ignores it. Falling back rather than raising
    is deliberate — a missing or broken export must make the Brain slower and heavier,
    never wrong or absent.
    """
    mode = (os.getenv("ANTAR_BRAIN_BACKEND") or "auto").lower()
    if mode == "torch":
        return None
    try:
        from app.second_brain.onnx_backend import OnnxTextEncoder, artifacts_for
        directory = artifacts_for(settings.BRAIN_EMBEDDING_MODEL)
        if directory is None:
            if mode == "onnx":
                print(f"  [WARN] ANTAR_BRAIN_BACKEND=onnx but no export for "
                      f"{settings.BRAIN_EMBEDDING_MODEL} — falling back to torch. "
                      f"Run: python scripts/export_onnx_models.py")
            return None
        enc = OnnxTextEncoder(directory)
        print(f"  [OK] Embedder loaded (onnx/{enc.variant}) -- "
              f"dim={enc.get_sentence_embedding_dimension()}")
        return enc
    except Exception as e:
        print(f"  [WARN] ONNX embedder unavailable ({e}) — falling back to torch")
        return None


def load_embedder() -> None:
    """Load the embedding model into memory (once, at FastAPI startup).

    Prefers the ONNX export (no torch); falls back to sentence-transformers.

    Loads from the local HF cache without touching the network. If the model was
    never cached (fresh machine + offline), it fails fast and the app runs
    DEGRADED — semantic recall disabled — instead of hanging on HTTP retries.
    """
    global _model
    _model = _load_onnx_embedder()
    if _model is not None:
        _model.encode(["Antar warm-up"], normalize_embeddings=True)
        return

    st = _load_sentence_transformers()
    if st is None:
        _model = None
        print("  [WARN] sentence_transformers not installed. Semantic search disabled.")
        return

    print(f"  Loading model: {settings.BRAIN_EMBEDDING_MODEL}")
    try:
        _model = st(settings.BRAIN_EMBEDDING_MODEL,
                    local_files_only=not _ALLOW_ONLINE)
        # Warm up with a test sentence
        _model.encode(["Antar warm-up"], normalize_embeddings=True)
        print(f"  [OK] Embedder loaded -- dim={_model.get_sentence_embedding_dimension()}")
    except Exception as e:
        _model = None
        print(f"  [WARN] Second Brain embedder unavailable (offline & not cached): {e}")
        print("  [WARN] Running DEGRADED — semantic recall disabled. Re-run once online "
              "(or set ANTAR_BRAIN_ONLINE=1) to download BAAI/bge-small-en-v1.5, ~33MB.")


def embed(texts: list[str] | str) -> np.ndarray:
    """Embed one or more DOCUMENT texts (no query prefix). Returns (n, 384) float32."""
    if _model is None:
        raise RuntimeError("Embedder not loaded — call load_embedder() at startup")
    if isinstance(texts, str):
        texts = [texts]
    return _model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def embed_query(text: str) -> np.ndarray:
    """Embed a QUERY text with the BGE asymmetric prefix. Returns shape (768,).

    Always use this for user questions / search queries.
    Use embed() for indexing documents (FIR MO fields, investigation summaries).
    """
    if _model is None:
        raise RuntimeError("Embedder not loaded — call load_embedder() at startup")
    prefixed = f"{_BGE_QUERY_PREFIX}{text}"
    arr = _model.encode([prefixed], normalize_embeddings=True, show_progress_bar=False)[0]
    # The index stores documents as [text | vision] (768). A text-only query must be
    # duplicated across both halves so it scores against the summary AND the image
    # description: [T|V] · [Q|Q]/√2 = (T·Q + V·Q)/√2. Dividing by √2 keeps the query
    # L2-normalised. Returning the bare 384 vector (a regression) made queries
    # un-multipliable against the 768 matrix and silently broke store-loaded recall.
    combined = np.concatenate([arr, arr]) / np.sqrt(2.0)
    return combined.astype(np.float32)


def embed_query_with_terms(text: str, terms: list[str] | None = None) -> np.ndarray:
    """QUERY-space vector (768) for a terms-enriched question.

    `embed_with_terms()` is a DOCUMENT embedder: 384-dim and deliberately WITHOUT the BGE
    query prefix. Retrieval was calling it to build a query vector, so the terms path
    produced a 384 vector against the 768 index and `_numpy_search` died with
    "matmul: size 384 is different from 768" (semantic_recall then swallowed it and
    returned no hits). Query vectors must be built here, once, in query space.
    """
    if _model is None:
        raise RuntimeError("Embedder not loaded — call load_embedder() at startup")
    prefix = " | ".join(t for t in (terms or []) if t)
    enriched = f"{prefix} — {text}" if prefix else text
    arr = _model.encode([f"{_BGE_QUERY_PREFIX}{enriched}"],
                        normalize_embeddings=True, show_progress_bar=False)[0]
    return (np.concatenate([arr, arr]) / np.sqrt(2.0)).astype(np.float32)


def embed_with_terms(text: str, terms: list[str] | None = None) -> np.ndarray:
    """Embed document text with prepended entity terms for richer semantic signal.

    Used during ingestion (documents), so NO query prefix.
    Prefixes the summary with pipe-separated entity terms (suspect names,
    aliases, zones, crime types, FIR numbers) so the vector captures both
    narrative semantics AND entity identity. Returns shape (384,).
    """
    prefix = " | ".join(t for t in (terms or []) if t)
    enriched = f"{prefix} — {text}" if prefix else text
    vec = embed(enriched)
    return vec[0] if vec.ndim == 2 else vec


def get_model() -> SentenceTransformer:
    if _model is None:
        raise RuntimeError("Embedder not loaded")
    return _model


async def get_visual_description(image_urls: list[str]) -> str:
    """Generate a textual description of an image using Qwen-3.6-Vision."""
    from app.services.quickml import quickml_vision_generate
    system = "You are a forensic image analyst. Describe this image in granular detail. Focus on entities, people, vehicles, weapons, colors, license plates, and locations."
    user = "Describe all forensic evidence and entities in this image."
    try:
        desc = await quickml_vision_generate(system=system, user=user, images=image_urls)
        return desc
    except Exception as e:
        print(f"  ⚠️  Vision API error: {e}")
        return ""


async def embed_multimodal(text: str, image_urls: list[str] | None = None, terms: list[str] | None = None) -> np.ndarray:
    """
    Generate a 768-dim concatenated [Text | Vision] embedding.
    """
    # 1. Text embedding (384-dim)
    text_emb = embed_with_terms(text, terms)
    
    # 2. Vision embedding (384-dim) via text description
    vision_emb = np.zeros(384, dtype=np.float32)
    if image_urls:
        desc = await get_visual_description(image_urls)
        if desc:
            v = embed(desc)
            vision_emb = v[0] if v.ndim == 2 else v
            
    # 3. Concatenate to 768-dim
    combined = np.concatenate([text_emb, vision_emb])
    
    # 4. L2 normalize
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm
        
    return combined.astype(np.float32)
