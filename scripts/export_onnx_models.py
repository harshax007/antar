"""
Antar — export the Second Brain models to ONNX (final_backend.md §4 step 6).

torch + transformers are the largest items in the deploy footprint: 688 MB of the
1,118 MB package closure, against a 2 GB budget that is currently 755 MB over
(docs/footprint/baseline.md). The weights themselves are tiny — the framework is the
cost. Exporting the same weights to ONNX lets the backend run them on onnxruntime, which
needs neither torch nor transformers at runtime, and INT8 quantisation shrinks the
weights about fourfold on top of that.

    python scripts/export_onnx_models.py                 # every model the backend can load
    python scripts/export_onnx_models.py --model BAAI/bge-small-en-v1.5
    python scripts/export_onnx_models.py --no-quantize   # fp32 only

Writes, per model, into models/onnx/<slug>/:
    model.onnx        fp32 export
    model_int8.onnx   dynamically quantised
    tokenizer.json    the fast tokenizer, loaded at runtime by `tokenizers` (no transformers)
    meta.json         pooling mode, normalisation, max sequence length, dim, parity scores

This script is a BUILD-TIME tool and the only place torch is still required: it loads the
cached sentence-transformers model to export it, then compares the ONNX output against
that same torch model. It refuses to mark an export good unless the parity check passes,
so a bad export can never quietly degrade retrieval.

Runtime never imports this file — see app/second_brain/onnx_backend.py.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

if os.getenv("ANTAR_BRAIN_ONLINE") != "1":                 # same rule as main.py
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_ROOT = ROOT / "models" / "onnx"
OPSET = 17

# Parity gates. Cosine is against the torch embedding of the same text; anything below
# this would change which cases the Brain surfaces.
MIN_COSINE_FP32 = 0.9999
MIN_COSINE_INT8 = 0.995

# Texts that exercise what Antar actually embeds: FIR narrative, MO wording, Kannada,
# names, and the BGE query prefix.
PROBES = [
    "chain snatching near the bus stand around 9pm, accused fled on a pulsar motorcycle",
    "house break-in during daytime, gold ornaments and cash stolen from bedroom almirah",
    "two wheeler theft from apartment parking, no CCTV coverage",
    "ಮನೆ ಕಳ್ಳತನ ರಾತ್ರಿ ವೇಳೆ ನಡೆದಿದೆ, ಚಿನ್ನಾಭರಣ ಕಳವು",
    "ಸರಗಳ್ಳತನ ಪ್ರಕರಣ ಬೆಂಗಳೂರು ನಗರ",
    "fraud using UPI collect request, victim transferred 45000 to unknown account",
    "Represent this sentence for searching relevant passages: theft hotspots in Mysuru",
    "accused ACC-KA-500777 absconding, pending trial",
]
PAIR_PROBES = [(PROBES[0], p) for p in PROBES]


def _slug(repo: str) -> str:
    return repo.replace("/", "--")


def _sizes(path: Path) -> str:
    """Size including external data: a large fp32 export is a small .onnx graph plus a
    .onnx.data weights file, and reporting only the graph made it look like 0.1 MB."""
    total = path.stat().st_size + sum(
        p.stat().st_size for p in path.parent.glob(path.name + ".data"))
    return f"{total / 1048576:.1f} MB"


def _export_transformer(hf_model, tokenizer, dest: Path, kind: str) -> Path:
    """Trace the HF module to ONNX with dynamic batch and sequence axes."""
    import torch

    class Wrapper(torch.nn.Module):
        def __init__(self, inner, kind):
            super().__init__()
            self.inner = inner
            self.kind = kind

        def forward(self, input_ids, attention_mask, token_type_ids=None):
            kw = {"input_ids": input_ids, "attention_mask": attention_mask}
            if token_type_ids is not None:
                kw["token_type_ids"] = token_type_ids
            out = self.inner(**kw)
            # embedder -> token vectors (pooled outside); cross-encoder -> logits
            return out.last_hidden_state if self.kind == "embedder" else out.logits

    enc = tokenizer(["probe text one", "probe two"], padding=True, truncation=True,
                    max_length=32, return_tensors="pt")
    names = ["input_ids", "attention_mask"] + (["token_type_ids"] if "token_type_ids" in enc else [])
    args = tuple(enc[n] for n in names)
    out_name = "last_hidden_state" if kind == "embedder" else "logits"
    dyn = {n: {0: "batch", 1: "sequence"} for n in names}
    dyn[out_name] = {0: "batch", 1: "sequence"} if kind == "embedder" else {0: "batch"}

    path = dest / "model.onnx"
    model = Wrapper(hf_model.eval(), kind).eval()
    with torch.no_grad():
        torch.onnx.export(model, args, str(path), input_names=names, output_names=[out_name],
                          dynamic_axes=dyn, opset_version=OPSET, do_constant_folding=True)
    return path


def _quantize(fp32: Path) -> Path | None:
    """Dynamic INT8. Measured best config: unsigned weights, per channel.

    Compared on all-MiniLM-L6-v2 against torch (min cosine over the probe set):
        QInt8  per-tensor  0.915      QInt8  per-channel  0.987
        QUInt8 per-tensor  0.954      QUInt8 per-channel  0.990
    Even the best still misses the parity gate, so the exporter writes the file and
    records the drift, and the runtime keeps fp32 unless the gate passes. The framework,
    not the weights, is what this step is really removing: fp32 ONNX already drops torch.
    """
    from onnxruntime.quantization import QuantType, quantize_dynamic

    int8 = fp32.parent / "model_int8.onnx"
    try:
        quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QUInt8,
                         per_channel=True, extra_options={"MatMulConstBOnly": True})
        return int8
    except Exception as e:                                  # keep fp32; never fail the build
        print(f"    quantisation failed ({e}) — fp32 only")
        return None


def export_one(repo: str, kind: str, quantize: bool) -> dict:
    from sentence_transformers import CrossEncoder, SentenceTransformer

    print(f"== {repo}  ({kind})")
    dest = OUT_ROOT / _slug(repo)
    dest.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    if kind == "embedder":
        st = SentenceTransformer(repo, local_files_only=True)
        transformer = st[0]
        hf_model, tokenizer = transformer.auto_model, transformer.tokenizer
        max_len = int(transformer.max_seq_length)
        pool_cfg = st[1].get_config_dict()
        pooling = "cls" if pool_cfg.get("pooling_mode_cls_token") else "mean"
        normalize = any("Normalize" in type(m).__name__ for m in st)
        dim = int(st.get_sentence_embedding_dimension())
        torch_ref = st
    else:
        ce = CrossEncoder(repo, max_length=512)
        hf_model, tokenizer = ce.model, ce.tokenizer
        max_len, pooling, normalize, dim = 512, None, False, 1
        torch_ref = ce

    fp32 = _export_transformer(hf_model, tokenizer, dest, kind)
    print(f"    fp32  {_sizes(fp32)}")
    int8 = _quantize(fp32) if quantize else None
    if int8:
        print(f"    int8  {_sizes(int8)}")

    # Tokenizer for runtime: the fast tokenizer's own file, read by `tokenizers` alone.
    src_tok = Path(tokenizer.name_or_path) / "tokenizer.json"
    if not src_tok.exists():
        tokenizer.save_pretrained(str(dest / "_tok"))
        src_tok = dest / "_tok" / "tokenizer.json"
    shutil.copyfile(src_tok, dest / "tokenizer.json")
    shutil.rmtree(dest / "_tok", ignore_errors=True)

    meta = {"repo": repo, "kind": kind, "pooling": pooling, "normalize": normalize,
            "max_seq_length": max_len, "dim": dim, "opset": OPSET,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "pad_token_id": int(tokenizer.pad_token_id or 0),
            "has_token_type_ids": "token_type_ids" in tokenizer("x"),
            "files": {"fp32": fp32.name, "int8": int8.name if int8 else None}}
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    meta["parity"] = _check_parity(dest, torch_ref, kind)
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    meta["seconds"] = round(time.time() - t0, 1)
    return meta


def _check_parity(dest: Path, torch_ref, kind: str) -> dict:
    """Compare ONNX output against the torch model that produced it."""
    import numpy as np
    from app.second_brain.onnx_backend import OnnxCrossEncoder, OnnxTextEncoder

    result: dict = {}
    for variant in ("fp32", "int8"):
        path = dest / ("model.onnx" if variant == "fp32" else "model_int8.onnx")
        if not path.exists():
            continue
        if kind == "embedder":
            onnx_enc = OnnxTextEncoder(dest, variant=variant)
            a = np.asarray(torch_ref.encode(PROBES, normalize_embeddings=True))
            b = onnx_enc.encode(PROBES, normalize_embeddings=True)
            cos = [float(np.dot(x, y)) for x, y in zip(a, b)]
            gate = MIN_COSINE_FP32 if variant == "fp32" else MIN_COSINE_INT8
            result[variant] = {"min_cosine": round(min(cos), 6),
                               "mean_cosine": round(float(np.mean(cos)), 6),
                               "gate": gate, "pass": min(cos) >= gate}
        else:
            onnx_ce = OnnxCrossEncoder(dest, variant=variant)
            a = np.asarray(torch_ref.predict(PAIR_PROBES), dtype=np.float32).ravel()
            b = np.asarray(onnx_ce.predict(PAIR_PROBES), dtype=np.float32).ravel()
            order_same = list(np.argsort(-a)) == list(np.argsort(-b))
            result[variant] = {"max_abs_logit_diff": round(float(np.max(np.abs(a - b))), 5),
                               "ranking_identical": bool(order_same),
                               "pass": bool(order_same) and float(np.max(np.abs(a - b))) < (
                                   0.01 if variant == "fp32" else 0.5)}
        verdict = "PASS" if result[variant]["pass"] else "FAIL"
        print(f"    parity {variant}: {verdict}  {result[variant]}")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10) + chr(10))[0])
    ap.add_argument("--model", action="append", help="repo id; repeatable")
    ap.add_argument("--no-quantize", action="store_true")
    args = ap.parse_args()

    if args.model:
        # Explicit models keep this script importable without the app's settings stack,
        # so a slim Docker builder stage can run it with just torch + onnx installed.
        targets = [(m, "cross-encoder" if "cross-encoder" in m else "embedder") for m in args.model]
    else:
        from app.core.settings import settings
        from app.second_brain.reranker import _CROSS_ENCODER_MODEL

        # Everything the backend might load: the configured embedder, the one the deploy
        # image pins (Dockerfile / app-config.json), and the reranker.
        repos = {settings.BRAIN_EMBEDDING_MODEL, "BAAI/bge-small-en-v1.5"}
        targets = [(r, "embedder") for r in sorted(repos)]
        targets.append((_CROSS_ENCODER_MODEL, "cross-encoder"))

    results = []
    for repo, kind in targets:
        try:
            results.append(export_one(repo, kind, not args.no_quantize))
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {e}")
            results.append({"repo": repo, "kind": kind, "error": str(e)})
        print()

    print("summary")
    failed = 0
    for r in results:
        if "error" in r:
            failed += 1
            print(f"  {r['repo']:<44} ERROR {r['error'][:60]}")
            continue
        par = r.get("parity", {})
        # Only fp32 decides success: it is the variant the runtime loads. int8 is
        # best-effort — it is written either way, and the loader ignores it unless its
        # own parity passed.
        ok = par.get("fp32", {}).get("pass", False)
        failed += 0 if ok else 1
        bits = " ".join(f"{k}:{'ok' if v.get('pass') else 'FAIL'}" for k, v in par.items())
        print(f"  {r['repo']:<44} {bits}   {r.get('seconds', 0)}s")
    print()
    print(f"artifacts in {OUT_ROOT}")
    int8_rejected = [r["repo"] for r in results
                     if r.get("parity", {}).get("int8", {}).get("pass") is False]
    if int8_rejected:
        print("int8 missed the parity gate for " + ", ".join(int8_rejected) +
              " — those load fp32, which still removes torch from the runtime")
    if failed:
        print(f"{failed} model(s) failed fp32 parity — the runtime keeps using torch for "
              f"those")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
