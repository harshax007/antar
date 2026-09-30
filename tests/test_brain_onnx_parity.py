"""
The ONNX Second Brain backend must return what the torch backend returns
(final_backend.md §4 step 6).

torch + transformers are 688 MB of the deploy footprint; the ONNX path runs the same
weights on onnxruntime + tokenizers, without either. That is only worth doing if
retrieval is unchanged, so these tests compare the two backends directly rather than
trusting the export.

Skipped when no export exists (`python scripts/export_onnx_models.py`) or when
sentence-transformers is absent — there is nothing to compare in either case.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core.settings import settings

onnx_backend = pytest.importorskip("app.second_brain.onnx_backend")

TEXTS = [
    "chain snatching near the bus stand around 9pm, accused fled on a motorcycle",
    "house break-in during daytime, gold ornaments stolen from the bedroom",
    "ಮನೆ ಕಳ್ಳತನ ರಾತ್ರಿ ವೇಳೆ ನಡೆದಿದೆ, ಚಿನ್ನಾಭರಣ ಕಳವು",
    "fraud using UPI collect request, victim transferred 45000",
    "",                                   # empty string must not blow up the tokenizer
    "x" * 4000,                           # far past max_seq_length: must truncate, not error
]


def _artifacts(repo: str):
    d = onnx_backend.artifacts_for(repo)
    if d is None:
        pytest.skip(f"no ONNX export for {repo} — run scripts/export_onnx_models.py")
    return d


def _torch_encoder(repo: str):
    st = pytest.importorskip("sentence_transformers")
    try:
        return st.SentenceTransformer(repo, local_files_only=True)
    except Exception as e:
        pytest.skip(f"torch embedder unavailable: {e}")


def test_embeddings_match_torch():
    """Cosine against the torch embedding of the same text, per text.

    The gate is deliberately tight: the Brain ranks by cosine, so a drift of a few
    thousandths can reorder which case an officer is shown first.
    """
    repo = settings.BRAIN_EMBEDDING_MODEL
    directory = _artifacts(repo)
    torch_model = _torch_encoder(repo)

    enc = onnx_backend.OnnxTextEncoder(directory)
    a = np.asarray(torch_model.encode(TEXTS, normalize_embeddings=True))
    b = enc.encode(TEXTS, normalize_embeddings=True)

    assert b.shape == a.shape
    cos = [float(np.dot(x, y)) for x, y in zip(a, b)]
    worst = min(cos)
    gate = 0.995 if enc.variant == "int8" else 0.9999
    assert worst >= gate, (
        f"ONNX ({enc.variant}) drifted from torch: worst cosine {worst:.6f} < {gate}. "
        f"per-text: {[round(c, 5) for c in cos]}")


def test_embeddings_are_normalised_and_finite():
    directory = _artifacts(settings.BRAIN_EMBEDDING_MODEL)
    vecs = onnx_backend.OnnxTextEncoder(directory).encode(TEXTS, normalize_embeddings=True)
    assert np.isfinite(vecs).all(), "non-finite values in embeddings"
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4), f"not unit vectors: {norms}"


def test_batching_does_not_change_results():
    """Padding differs between batch sizes; masked pooling must make that irrelevant."""
    directory = _artifacts(settings.BRAIN_EMBEDDING_MODEL)
    enc = onnx_backend.OnnxTextEncoder(directory)
    batched = enc.encode(TEXTS, normalize_embeddings=True, batch_size=len(TEXTS))
    one_by_one = np.vstack([enc.encode([t], normalize_embeddings=True) for t in TEXTS])
    assert np.allclose(batched, one_by_one, atol=1e-4), (
        "results depend on batch size — pooling is probably counting padding tokens")


def test_reranker_ranking_matches_torch():
    """The reranker only has to agree on ORDER: the score feeds MMR, the order decides."""
    from app.second_brain.reranker import _CROSS_ENCODER_MODEL

    directory = _artifacts(_CROSS_ENCODER_MODEL)
    st = pytest.importorskip("sentence_transformers")
    try:
        torch_ce = st.CrossEncoder(_CROSS_ENCODER_MODEL, max_length=512)
    except Exception as e:
        pytest.skip(f"torch cross-encoder unavailable: {e}")

    query = "chain snatching near a bus stand at night"
    passages = [
        "chain snatching reported near the bus stand, accused on a motorcycle at 9pm",
        "house break-in during daytime, gold ornaments stolen",
        "two wheeler theft from apartment parking",
        "cheating case: UPI collect request fraud of 45000 rupees",
        "murder case under investigation, accused arrested",
    ]
    pairs = [(query, p) for p in passages]
    a = np.asarray(torch_ce.predict(pairs), dtype=np.float32).ravel()
    b = onnx_backend.OnnxCrossEncoder(directory).predict(pairs)

    assert list(np.argsort(-a)) == list(np.argsort(-b)), (
        f"ONNX reranker orders results differently: torch {np.argsort(-a)} vs "
        f"onnx {np.argsort(-b)}  (torch scores {a}, onnx {b})")


def test_loader_falls_back_when_export_is_missing(tmp_path, monkeypatch):
    """A missing export must degrade to torch, never break the Brain.

    This is the safety property of the whole step: ONNX is an optimisation, and an
    optimisation that can take retrieval offline is not worth having.
    """
    monkeypatch.setenv("ANTAR_ONNX_DIR", str(tmp_path))      # empty dir: no artifacts
    assert onnx_backend.artifacts_for(settings.BRAIN_EMBEDDING_MODEL) is None

    from app.second_brain import embedder
    assert embedder._load_onnx_embedder() is None, (
        "the ONNX loader returned a model when no artifacts exist")


def test_torch_backend_can_be_forced(monkeypatch):
    """ANTAR_BRAIN_BACKEND=torch is the rollback switch; it must bypass ONNX."""
    monkeypatch.setenv("ANTAR_BRAIN_BACKEND", "torch")
    from app.second_brain import embedder
    assert embedder._load_onnx_embedder() is None
