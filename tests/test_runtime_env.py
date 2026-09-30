"""
The BLAS thread cap main.py installs at import time (final_backend.md §4 step 2b).

numpy and scipy each bundle OpenBLAS, which reserves a workspace per CPU thread on first
import: 758 MB of private memory on a 12-core machine against 20 MB at one thread
(docs/footprint/blas-threads.md). The deployed container already sets OMP_NUM_THREADS=1
(Dockerfile, app-config.json); main.py sets the same default so a local run, a test run
and a deploy whose env var went missing all behave alike.

Each test imports main in a subprocess with a controlled environment, because the thread
count is read once, when OpenBLAS is first imported — it cannot be re-tested in a process
that has already imported numpy.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BLAS_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")

# Imports main, then reports the environment and the live BLAS pools.
PROBE = (
    "import main, json, os" + chr(10) +
    "import numpy, scipy.linalg" + chr(10) +
    "from threadpoolctl import threadpool_info" + chr(10) +
    "print('@@' + json.dumps({"
    "'env': {v: os.environ.get(v) for v in "
    "('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},"
    "'pools': [(i.get('internal_api'), i.get('num_threads')) for i in threadpool_info()]"
    "}))"
)


def _probe(env_overrides: dict[str, str]) -> dict:
    pytest.importorskip("threadpoolctl")           # ships with scikit-learn
    env = {k: v for k, v in os.environ.items() if k not in BLAS_VARS}
    env.update(env_overrides)
    env["ANTAR_BRAIN_ONLINE"] = "0"                # never touch the network from a test
    proc = subprocess.run([sys.executable, "-c", PROBE], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=300)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("@@")), None)
    assert line, f"probe failed (exit {proc.returncode}):{chr(10)}{proc.stdout[-2000:]}" \
                 f"{chr(10)}{proc.stderr[-2000:]}"
    return json.loads(line[2:])


def test_importing_main_caps_blas_threads():
    """With nothing set, importing main pins every BLAS pool to one thread."""
    out = _probe({})
    assert out["env"]["OMP_NUM_THREADS"] == "1"
    assert out["env"]["OPENBLAS_NUM_THREADS"] == "1"
    assert out["env"]["MKL_NUM_THREADS"] == "1"
    blas = [n for api, n in out["pools"] if api in ("openblas", "mkl", "blis")]
    assert blas, "no BLAS pool reported — threadpoolctl saw nothing to check"
    assert all(n == 1 for n in blas), f"BLAS pools not capped: {out['pools']}"


def test_operator_override_wins():
    """An operator who set a thread count keeps it — including for BLAS.

    The deployed container sets OMP_NUM_THREADS itself (Dockerfile, app-config.json), and
    an operator tuning a larger instance must be able to raise it without editing code.
    This has to hold for the BLAS pool, not merely for the variable: OpenBLAS reads
    OPENBLAS_NUM_THREADS in preference to OMP_NUM_THREADS, so pinning its variable
    independently would silently cap someone who raised OMP_NUM_THREADS. That is exactly
    what the first version of the cap did, and this test caught it.
    """
    out = _probe({"OMP_NUM_THREADS": "3"})
    assert out["env"]["OMP_NUM_THREADS"] == "3"
    assert out["env"]["OPENBLAS_NUM_THREADS"] is None, (
        "main.py pinned OPENBLAS_NUM_THREADS even though the operator set OMP_NUM_THREADS "
        "— that overrides their intent")
    blas = [n for api, n in out["pools"] if api in ("openblas", "mkl", "blis")]
    assert all(n == 3 for n in blas), f"override not honoured: {out['pools']}"


def test_cap_is_set_before_numpy_is_imported():
    """Ordering guard: the cap only works if nothing imports numpy before it.

    A future import added above the block in main.py would silently restore the old
    memory cost, so assert the ordering in the source rather than trusting review.
    """
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    cap = src.index("_BLAS_VARS")
    for offender in ("import numpy", "import pandas", "import scipy", "import sklearn",
                     "from app.", "import app."):
        pos = src.find(offender)
        assert pos == -1 or pos > cap, (
            f"{offender!r} appears before the BLAS cap in main.py — numpy may already be "
            f"imported by then, which silently restores ~750 MB of thread buffers")
