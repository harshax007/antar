# Running Antar locally

One rule: **always use the project's own virtual environment.** Never the interpreter that
happens to be first on `PATH`.

## The environment

`D:\Project\.venv` — Python **3.11.15**, torch-free, **509 MB**.

It was built from `requirements-runtime.txt`, which is the ONNX path: `onnxruntime` +
`tokenizers` instead of `torch` + `sentence-transformers`. That is the whole point of the
runtime work — the same environment with torch is ~2.5 GB and will not fit the deployment
budget. `requirements.txt` (with torch) is only needed to *export* the ONNX models
(`scripts/export_onnx_models.py`) or to run the torch-parity test.

Rebuilding it from scratch:

```powershell
C:\Users\hx07-\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe -m venv D:\Project\.venv
D:\Project\.venv\Scripts\python.exe -m pip install --upgrade pip
D:\Project\.venv\Scripts\python.exe -m pip install -r D:\Project\requirements-runtime.txt pytest==8.3.4 psutil
```

`pytest` and `psutil` are test-only and deliberately absent from both requirements files —
nothing in the deployed image needs them. `psutil` matters, though: without it the Second
Brain **working-set guard** (`test_brain_vec_store.py` — the test asserting RSS stays under
25 MB across 20k rows) silently skips, and that test is the reason a 100k-FIR corpus fits
inside a 2 GB box.

Python 3.12 is also installed on this machine. Do not use it: `scipy==1.12.0` and
`scikit-learn==1.4.1.post1` have never been tested there.

## Start the backend

```powershell
cd D:\Project
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Without activating, call the interpreter by path — this is the safer habit:

```powershell
D:\Project\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000/docs>.

### What a healthy boot looks like

`Application startup complete` appears within seconds and `/api/health` answers
immediately. Warm-up then runs in the background for **1–2 minutes**:

| Line | Meaning |
|---|---|
| `SECURITY: identity is the unsigned X-Role/X-Officer header` | expected in `development`; set `ANTAR_AUTH_SECRET` before anything public |
| `SECURITY: CRON_SECRET_KEY is default/short` | same |
| `Loading Second Brain embedder` then a **20 s pause** | the Catalyst Data Store fetch timing out. Documented, not a hang — the local store holds only the FIR tier, so it falls back to 3 planted summaries |
| `Forecast scan: N active alert(s)` | the cube rebuilt (~35 s over 1M FIRs) |
| `Background warmup completed successfully!` | done |

`LLM decompose failed: TimeoutError` during warm-up is QuickML being cold, not a fault.
The deterministic path answers without it.

### Checks worth running

```bash
curl -s http://127.0.0.1:8000/api/health
```

`brain_backend` must read `onnx/fp32`. Then:

```bash
curl -s -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d "{\"text\":\"which district has the most kidnapping cases?\"}"
```

The request field is **`text`**, not `message`.

## Tests

```powershell
cd D:\Project
.\.venv\Scripts\python.exe -m pytest -q
```

Takes about 10 minutes.

## The frontend

Still on E:. It reads `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` from
`.env.development`, which matches the backend default, and the backend already allows
`http://localhost:3000`. Nothing to configure:

```powershell
cd E:\Antar_FinalBuild_Dev\antar-frontend
npm run dev
```

## One trap worth knowing about

**scikit-learn must not load before onnxruntime.** Both wheels ship their own OpenMP
runtime, and on Windows this kills the interpreter outright:

```python
import sklearn; import onnxruntime   # Windows fatal exception: access violation
import onnxruntime; import sklearn   # fine
```

No traceback, exit code 139, nothing in the log after `Loading Second Brain embedder`.
`main.py` and `tests/conftest.py` both import `onnxruntime` up front to pin the order, so
this is handled — but if you write a new entry point that touches both, import
`onnxruntime` first.

A torch-bearing environment hides this, because torch loads a compatible OpenMP and wins
the race. `Dockerfile.onnx` installs no torch, so the deployed image is exactly the
configuration that crashes.
