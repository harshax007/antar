"""
Antar — ONNX runtime backend for the Second Brain models (final_backend.md §4 step 6).

Runs the same weights as the sentence-transformers path, without torch or transformers:
only `onnxruntime`, `tokenizers` and numpy. That matters because torch + transformers are
688 MB of the 1,118 MB package closure, against a budget this deployment is currently
755 MB over (docs/footprint/baseline.md) — while the weights themselves are ~90 MB.

Artifacts come from `scripts/export_onnx_models.py`, which refuses to publish an export
that does not match the torch output on a fixture. This module deliberately contains no
export logic and never imports torch: if the artifacts are missing or unreadable, the
caller falls back to sentence-transformers (see embedder.py / reranker.py), so the Brain
degrades to "slower and heavier", never to "wrong".

The pipeline reproduces sentence-transformers exactly, because a mismatch here would
silently change which cases the Brain surfaces:
  tokenize (same tokenizer.json, same max_seq_length)
  -> ONNX forward
  -> pooling: CLS for BGE, mean-over-attention-mask for MiniLM (read from meta.json)
  -> optional L2 normalisation
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent / "models" / "onnx"


def artifacts_root() -> Path:
    """Where exported models live. ANTAR_ONNX_DIR overrides, for a container layout."""
    return Path(os.getenv("ANTAR_ONNX_DIR") or _DEFAULT_ROOT)


def artifacts_for(repo: str) -> Path | None:
    """The export directory for a repo id, if it holds a usable model."""
    d = artifacts_root() / repo.replace("/", "--")
    return d if (d / "meta.json").exists() and (d / "tokenizer.json").exists() else None


def _session(model_path: Path, threads: int | None = None):
    import onnxruntime as ort

    opts = ort.SessionOptions()
    # One thread by default, for the same reason main.py caps BLAS threads: a per-thread
    # arena costs memory, and measured on this workload more threads did not help —
    # reranking 20 passages took 184 ms at 1 thread and 203 ms at 4, while private memory
    # rose from 179 MB to 275 MB (docs/footprint/onnx-backend.md). ANTAR_ONNX_THREADS
    # raises it for a machine where that trade-off differs.
    try:
        threads = int(os.getenv("ANTAR_ONNX_THREADS") or 0) or threads or 1
    except ValueError:
        threads = 1
    opts.intra_op_num_threads = threads
    opts.inter_op_num_threads = 1
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(model_path), opts, providers=["CPUExecutionProvider"])


class _OnnxModel:
    """Shared tokenizer + session plumbing."""

    def __init__(self, directory: Path, variant: str = "auto"):
        from tokenizers import Tokenizer

        self.dir = Path(directory)
        self.meta = json.loads((self.dir / "meta.json").read_text(encoding="utf-8"))
        int8, fp32 = self.dir / "model_int8.onnx", self.dir / "model.onnx"
        # "auto" takes int8 only when the export recorded that it PASSED the parity gate.
        # Presence on disk is not enough: quantisation can drift badly (measured: cosine
        # 0.82 against torch for MiniLM), and the exporter still writes the file so the
        # drift is visible. Loading it because it exists would silently degrade recall.
        int8_ok = bool(self.meta.get("parity", {}).get("int8", {}).get("pass"))
        if variant == "int8" or (variant == "auto" and int8.exists() and int8_ok):
            path, self.variant = int8, "int8"
        else:
            path, self.variant = fp32, "fp32"
        if not path.exists():
            raise FileNotFoundError(f"no ONNX model at {path}")
        self.session = _session(path)
        self.tokenizer = Tokenizer.from_file(str(self.dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=int(self.meta["max_seq_length"]))
        self.tokenizer.enable_padding(pad_id=int(self.meta.get("pad_token_id", 0)),
                                      pad_token="[PAD]")
        self._inputs = {i.name for i in self.session.get_inputs()}

    def _encode_batch(self, encodings) -> dict:
        feed = {
            "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
        }
        if "token_type_ids" in self._inputs:
            feed["token_type_ids"] = np.array([e.type_ids for e in encodings], dtype=np.int64)
        return {k: v for k, v in feed.items() if k in self._inputs}


class OnnxTextEncoder(_OnnxModel):
    """Drop-in replacement for SentenceTransformer.encode() as the Brain uses it."""

    def encode(self, texts, normalize_embeddings: bool = True, batch_size: int = 32,
               show_progress_bar: bool = False, **_ignored) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        texts = list(texts)
        if not texts:
            return np.zeros((0, self.meta["dim"]), dtype=np.float32)

        out = []
        for start in range(0, len(texts), batch_size):
            chunk = texts[start:start + batch_size]
            enc = self.tokenizer.encode_batch(chunk)
            feed = self._encode_batch(enc)
            hidden = self.session.run(None, feed)[0]               # (b, seq, dim)
            mask = feed["attention_mask"].astype(np.float32)[..., None]
            if self.meta.get("pooling") == "cls":
                vecs = hidden[:, 0, :]
            else:                                                   # mean over real tokens
                vecs = (hidden * mask).sum(axis=1) / np.clip(mask.sum(axis=1), 1e-9, None)
            out.append(vecs.astype(np.float32))

        vecs = np.vstack(out)
        if normalize_embeddings or self.meta.get("normalize"):
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs = vecs / np.clip(norms, 1e-12, None)
        return vecs.astype(np.float32)

    def get_sentence_embedding_dimension(self) -> int:
        return int(self.meta["dim"])


class OnnxCrossEncoder(_OnnxModel):
    """Drop-in replacement for CrossEncoder.predict() over (query, passage) pairs."""

    def predict(self, pairs, batch_size: int = 32, **_ignored) -> np.ndarray:
        pairs = list(pairs)
        if not pairs:
            return np.zeros((0,), dtype=np.float32)
        scores = []
        for start in range(0, len(pairs), batch_size):
            chunk = pairs[start:start + batch_size]
            enc = self.tokenizer.encode_batch([(a, b) for a, b in chunk])
            logits = self.session.run(None, self._encode_batch(enc))[0]
            scores.append(np.asarray(logits, dtype=np.float32).reshape(len(chunk), -1)[:, 0])
        return np.concatenate(scores)
