# Second Brain on ONNX — measurements

Measured 2026-09-23, 12-CPU Windows laptop, Python 3.11.15, onnxruntime 1.30.0,
torch 2.13.0+cpu. Supports `final_backend.md` §4 step 6.

## What changed

The Brain's two models (embedder, cross-encoder reranker) can now run on onnxruntime
instead of sentence-transformers/torch. Same weights, exported by
`scripts/export_onnx_models.py` and served by `app/second_brain/onnx_backend.py`.
Selected with `ANTAR_BRAIN_BACKEND`: `auto` (default — ONNX when an export exists),
`onnx`, or `torch` to roll back. Both loaders fall back to torch if anything is missing,
so the Brain can get slower, never wrong.

## Parity: is it the same answer?

`scripts/export_onnx_models.py` checks every export against the torch model that produced
it, and `tests/test_brain_onnx_parity.py` re-checks on every test run.

| Model | Variant | Result |
|---|---|---|
| BAAI/bge-small-en-v1.5 | fp32 | **min cosine 1.000000** vs torch — PASS |
| BAAI/bge-small-en-v1.5 | int8 | min cosine 0.987 — **FAIL** (gate 0.995), not loaded |
| all-MiniLM-L6-v2 | fp32 | **min cosine 1.000000** — PASS |
| all-MiniLM-L6-v2 | int8 | min cosine 0.979 — **FAIL**, not loaded |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | fp32 | max logit diff **0.0**, ranking identical — PASS |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | int8 | quantisation errored (shape inference) — fp32 only |

Probes include Kannada, FIR/MO phrasing, the BGE query prefix, an empty string and a
4,000-character string.

### Why int8 is built but disabled

INT8 would save ~68 MB per model, but it moves the embedding. Dynamic quantisation
configs compared on all-MiniLM-L6-v2 (min cosine vs torch):

| Weights | Per-channel | Min cosine | Size |
|---|---|---|---|
| QInt8 | no | 0.915 | 21.7 MB |
| QInt8 | yes | 0.987 | 21.8 MB |
| QUInt8 | no | 0.954 | 21.7 MB |
| **QUInt8** | **yes** | **0.990** | 21.8 MB |

The exporter uses the best of these and still records a FAIL, because the Brain ranks by
cosine and a drift of ~1% can reorder near-ties — which case an officer sees first. The
loader takes int8 only when its recorded parity passed, so the file's presence is not
enough to enable it. **The framework, not the weights, is the saving: fp32 ONNX already
removes torch.**

## Runtime cost, both backends at one thread (production setting)

| | ONNX fp32 | torch | Change |
|---|---|---|---|
| RSS after loading both models | **195 MB** | 513 MB | −318 MB (−62%) |
| Private (reserved) | **179 MB** | 590 MB | −411 MB |
| Load time | **0.7 s** | 15.9 s | 23× faster |
| Embed one query (median of 40) | **7.5 ms** | 16.6 ms | 2.2× faster |
| Rerank 20 passages (median of 10) | 184 ms | 188 ms | parity |
| `torch` imported at all | **No** | Yes | — |

An earlier run appeared to show ONNX reranking 2.2× *slower* (164 ms vs 75 ms). That was
a thread mismatch: torch had all 12 CPUs while the ONNX session had 1. At equal threads
they are level.

More ONNX threads do not help this workload, so `intra_op_num_threads` stays at 1
(`ANTAR_ONNX_THREADS` overrides):

| Threads | Rerank ×20 | Private |
|---|---|---|
| 1 | 184 ms | 179 MB |
| 2 | 207 ms | 211 MB |
| 4 | 203 ms | 275 MB |

## Disk, for a torch-free serving image

Installed sizes from this environment (Windows; a Linux image will differ — `Dockerfile.onnx`
has not been built yet, so these are not image measurements):

| Removed | MB |
|---|---|
| torch | 499.5 |
| transformers | 106.3 |
| sympy | 72.1 |
| sentence-transformers | 2.0 |
| safetensors | 0.9 |
| **subtotal** | **680.8** |
| Baked HF model caches (3 models, no longer needed) | ~310 |

| Added | MB |
|---|---|
| onnxruntime | 44.3 |
| ONNX fp32 artifacts (bge-small + reranker, int8 dropped) | ~215 |

Net ≈ **−730 MB**, against a measured overage of 755 MB. `tokenizers` (7.4 MB) stays —
it reads `tokenizer.json` directly and does not need transformers.

## What is verified and what is not

Verified here: parity, memory, latency, 61 Brain tests, 6 parity tests, golden suite.
**Not verified: the image.** Docker Desktop was not running, so `Dockerfile.onnx` has
never been built and the image-size claim above is inferred from package sizes. Build it
and compare against the current `Dockerfile` before switching the deployment.
