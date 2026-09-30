"""
Antar — BLAS thread-cap benchmark (final_backend.md §4 step 2b).

numpy and scipy each bundle OpenBLAS, which reserves a workspace per thread at import
(measured 2026-09-22: +758 MB private at 12 threads vs +20 MB at 1). Capping the threads
is a one-line change, but it could slow the forecast fit, queries or the Brain models, so
this measures all three at each setting before a value is chosen.

    python scripts/bench_blas_threads.py                  # default (all CPUs), 1, 2, 4
    python scripts/bench_blas_threads.py --threads 1 2    # a subset
    python scripts/bench_blas_threads.py --skip-models    # no torch (faster)

Each setting runs in a fresh process, because BLAS reads its thread count once, at import.
Per setting it measures:
  * import cost of numpy / scipy / pandas / scikit-learn (private MB)
  * the full forecast fit for the real-record as-of (`app.forecast.run.compute`), timed,
    with every forecast row it would persist captured and compared across settings
  * the golden query suite (tests/golden_queries.py, offline path), two passes, timed and
    scored
  * Brain models: query embedding and cross-encoder rerank latency (loads torch)

Read-only against main.db: the forecast runs on a `mode=ro` SQLite connection behind a
proxy that absorbs only compute()'s final persist statements (capturing their rows) — any
other write fails loudly at the SQLite level. The golden suite uses the app's own query
path, exactly as a user question would. Model loads stay offline, as in main.py.
"""

from __future__ import annotations

import os

if os.getenv("ANTAR_BRAIN_ONLINE") != "1":                 # same rule as main.py
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import argparse
import json
import pickle
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NL = chr(10)
MARK = "@@BENCH_RESULT@@"
THREAD_VARS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
PERSIST_HEADS = ("BEGIN", "COMMIT", "ROLLBACK", "INSERT", "DELETE", "CREATE", "DROP")


class PersistCapture:
    """Wraps a read-only sqlite3 connection. Reads pass through; the persist statements
    compute() issues at its end are absorbed, and INSERT rows are kept for comparison."""

    def __init__(self, con):
        self._con = con
        self.captured: dict[str, list] = {}
        self.absorbed = 0

    def _is_persist(self, sql: str) -> bool:
        return sql.lstrip().split(None, 1)[0].upper() in PERSIST_HEADS

    def execute(self, sql, params=()):
        if self._is_persist(sql):
            self.absorbed += 1
            return self._con.execute("SELECT 1")
        return self._con.execute(sql, params)

    def executemany(self, sql, seq):
        if self._is_persist(sql):
            self.absorbed += 1
            table = sql.split("INTO", 1)[1].split()[0] if "INTO" in sql.upper() else "?"
            self.captured.setdefault(table, []).extend(list(seq))
            return None
        return self._con.executemany(sql, seq)

    def __getattr__(self, name):
        return getattr(self._con, name)


def _private_mb(proc) -> float:
    mi = proc.memory_info()
    return round((getattr(mi, "private", 0) or mi.rss) / 1048576, 1)


def child(out_file: str, skip_models: bool) -> dict:
    import psutil
    proc = psutil.Process()
    res: dict = {"threads_env": {v: os.environ.get(v) for v in THREAD_VARS},
                 "cpu_count": os.cpu_count(), "private_start_mb": _private_mb(proc)}

    t0 = time.perf_counter()
    import numpy  # noqa: F401
    import scipy.linalg  # noqa: F401
    import pandas  # noqa: F401
    import sklearn.linear_model  # noqa: F401
    res["import_s"] = round(time.perf_counter() - t0, 2)
    res["private_after_imports_mb"] = _private_mb(proc)
    try:
        from threadpoolctl import threadpool_info
        res["blas_pools"] = sorted({(p.get("internal_api"), p.get("num_threads"))
                                    for p in threadpool_info()}, key=str)
    except Exception:
        res["blas_pools"] = None

    # ── Forecast fit, read-only ──
    import sqlite3
    from app.core.db_path import DB_PATH
    from app.forecast import asof as asof_mod, run as frun, store
    db = os.environ.get("ANTAR_BENCH_DB") or DB_PATH
    if os.path.abspath(db) == os.path.abspath(DB_PATH):
        raise SystemExit("refusing to fit against the live database — run via the parent, "
                         "which takes a snapshot first")
    ro = sqlite3.connect(Path(db).as_uri() + "?mode=ro", uri=True, timeout=60)
    if store._meta(ro, "signature") != store._signature(ro):
        raise SystemExit("forecast cube is stale — start the backend once so it rebuilds, "
                         "then rerun (this benchmark never writes to main.db)")
    proxy = PersistCapture(ro)
    a = asof_mod.resolve(proxy, "real")
    t0 = time.perf_counter()
    summary = frun.compute(proxy, a)
    res["forecast_s"] = round(time.perf_counter() - t0, 1)
    res["forecast_as_of"] = summary["as_of"]
    res["forecast_models"] = summary["models"]
    rows = proxy.captured.get("forecast_output", [])
    fits = proxy.captured.get("forecast_models", [])
    res["forecast_rows"] = len(rows)
    res["private_after_forecast_mb"] = _private_mb(proc)
    with open(out_file, "wb") as f:
        pickle.dump({"rows": rows, "fits": fits}, f)
    ro.close()

    # ── Golden query suite, two passes ──
    import asyncio
    from tests.golden_queries import run_suite
    passes = []
    for _ in range(2):
        t0 = time.perf_counter()
        s = asyncio.run(run_suite(use_llm=False))
        passes.append({"s": round(time.perf_counter() - t0, 2), "passed": s["passed"],
                       "total": s["total"]})
    res["golden"] = passes
    res["private_after_queries_mb"] = _private_mb(proc)

    # ── Brain models (torch) ──
    if not skip_models:
        from app.second_brain import embedder
        from app.second_brain.reranker import reranker
        embedder.load_embedder()
        reranker.load()
        qs = ["chain snatching near a bus stand at night", "two wheeler theft from parking",
              "ಮನೆ ಕಳ್ಳತನ ರಾತ್ರಿ", "fraud using UPI collect request"]
        embedder.embed_query(qs[0])                         # warm
        lat = []
        for i in range(40):
            t0 = time.perf_counter()
            embedder.embed_query(qs[i % len(qs)])
            lat.append((time.perf_counter() - t0) * 1000)
        res["embed_query_ms_median"] = round(statistics.median(lat), 2)
        cands = [{"summary_text": f"FIR {i}: vehicle theft reported near market area, "
                                  f"accused fled on a motorcycle, case {i}"} for i in range(20)]
        if reranker.available:
            reranker.rerank(qs[1], [dict(c) for c in cands], 5)
            lat = []
            for _ in range(10):
                t0 = time.perf_counter()
                reranker.rerank(qs[1], [dict(c) for c in cands], 5)
                lat.append((time.perf_counter() - t0) * 1000)
            res["rerank20_ms_median"] = round(statistics.median(lat), 1)
        res["private_after_models_mb"] = _private_mb(proc)

    mi = proc.memory_info()
    res["peak_wset_mb"] = round(getattr(mi, "peak_wset", mi.rss) / 1048576, 1)
    res["private_end_mb"] = _private_mb(proc)
    return res


def _compare(base_file: str, other_file: str) -> dict:
    with open(base_file, "rb") as f:
        a = pickle.load(f)
    with open(other_file, "rb") as f:
        b = pickle.load(f)
    ka = {r[:5]: r[5:] for r in a["rows"]}
    kb = {r[:5]: r[5:] for r in b["rows"]}
    same_keys = set(ka) == set(kb)
    exact = sum(1 for k in ka if k in kb and ka[k] == kb[k])
    max_diff = 0.0
    for k in ka.keys() & kb.keys():
        for x, y in zip(ka[k], kb[k]):
            if x is not None and y is not None:
                max_diff = max(max_diff, abs(float(x) - float(y)))
    fits_same = sorted(a["fits"]) == sorted(b["fits"])
    return {"rows": len(ka), "same_units": same_keys, "rows_identical": exact,
            "max_abs_diff": max_diff, "fit_params_identical": fits_same}


def _snapshot(tmp: Path) -> Path:
    """One consistent copy of main.db, shared by every setting.

    Uses the SQLite backup API rather than a file copy: it is consistent even if the
    backend is running and writing. The copy is then switched out of WAL mode so the
    children can open it read-only — a WAL database needs its shared-index file rebuilt
    by a writer, which a read-only connection cannot do when no backend is up (that is
    exactly what broke the first attempt at this benchmark).
    """
    import sqlite3
    from app.core.db_path import DB_PATH

    dest = tmp / "bench_snapshot.db"
    print(f"   snapshotting main.db -> {dest} ...", flush=True)
    t0 = time.time()
    src = sqlite3.connect(DB_PATH, timeout=120)
    try:
        # A backend that died leaves a stale -shm/-wal pair behind. Until some connection
        # recovers it, even reading the database fails with "disk I/O error" (this is what
        # broke two earlier attempts). Opening read-write and checkpointing clears it.
        src.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        out = sqlite3.connect(dest, timeout=120)
        try:
            src.backup(out)
            out.execute("PRAGMA journal_mode=DELETE")
        finally:
            out.close()
    finally:
        src.close()
    print(f"   snapshot ready in {time.time() - t0:.0f}s "
          f"({dest.stat().st_size / 1048576:.0f} MB)", flush=True)
    return dest


def parent(settings: list[str], skip_models: bool) -> int:
    tmp = Path(tempfile.mkdtemp(prefix="antar_blas_"))
    snapshot = _snapshot(tmp)
    results = {}
    for s in settings:
        env = dict(os.environ)
        env["ANTAR_BENCH_DB"] = str(snapshot)
        for v in THREAD_VARS:
            env.pop(v, None)
            if s != "default":
                env[v] = s
        out_file = str(tmp / f"forecast_{s}.pkl")
        cmd = [sys.executable, __file__, "--child", out_file] + (["--skip-models"] if skip_models else [])
        print(f"== threads={s} ...", flush=True)
        t0 = time.time()
        p = subprocess.run(cmd, env=env, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        line = next((l for l in p.stdout.splitlines() if l.startswith(MARK)), None)
        if p.returncode != 0 or line is None:
            print(p.stdout[-3000:])
            print(p.stderr[-3000:])
            print(f"   FAILED (exit {p.returncode})")
            return 1
        r = json.loads(line[len(MARK):])
        r["wall_s"] = round(time.time() - t0, 1)
        r["_file"] = out_file
        results[s] = r
        # Persist after every setting: a run that is interrupted half way should not
        # throw away the settings that already finished (learned the hard way).
        partial = ROOT / "docs" / "footprint"
        partial.mkdir(parents=True, exist_ok=True)
        (partial / "blas-threads.partial.json").write_text(
            json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "_file"}
                        for k, v in results.items()}, indent=2), encoding="utf-8")
        print(f"   forecast {r['forecast_s']} s · golden {r['golden'][0]['s']}/{r['golden'][1]['s']} s "
              f"({r['golden'][1]['passed']}/{r['golden'][1]['total']}) · private end "
              f"{r['private_end_mb']} MB", flush=True)

    base = "default" if "default" in results else settings[0]
    for s, r in results.items():
        r["vs_" + base] = None if s == base else _compare(results[base]["_file"], r["_file"])

    L = ["# BLAS thread cap — benchmark", "",
         f"Measured {time.strftime('%Y-%m-%d %H:%M:%S')} · {os.cpu_count()} logical CPUs · "
         f"Python {sys.version.split()[0]} · generated by `scripts/bench_blas_threads.py`", "",
         "| Threads | Import private MB | After forecast MB | End private MB | Peak working set MB | "
         "Forecast fit s | Golden pass 1 / 2 s | Golden score | Embed ms | Rerank×20 ms |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for s, r in results.items():
        g = r["golden"]
        label = s if s != "default" else "default (" + str(r["cpu_count"]) + ")"
        L.append(f"| {label} | "
                 f"{r['private_after_imports_mb']} | {r['private_after_forecast_mb']} | "
                 f"{r['private_end_mb']} | {r['peak_wset_mb']} | {r['forecast_s']} | "
                 f"{g[0]['s']} / {g[1]['s']} | {g[1]['passed']}/{g[1]['total']} | "
                 f"{r.get('embed_query_ms_median', '—')} | {r.get('rerank20_ms_median', '—')} |")
    L += ["", f"Forecast outputs compared with `{base}` "
              f"(as-of {results[base]['forecast_as_of']}, {results[base]['forecast_rows']} rows, "
              f"{results[base]['forecast_models']} models):", "",
          "| Threads | Same units | Rows identical (as persisted, 4 dp) | Max abs diff | Fit parameters identical |",
          "|---|---|---|---|---|"]
    for s, r in results.items():
        c = r["vs_" + base]
        if c:
            L.append(f"| {s} | {c['same_units']} | {c['rows_identical']}/{c['rows']} | "
                     f"{c['max_abs_diff']:.2e} | {c['fit_params_identical']} |")
    md = NL.join(L) + NL
    print()
    print(md)
    out = ROOT / "docs" / "footprint"
    out.mkdir(parents=True, exist_ok=True)
    for r in results.values():
        r.pop("_file", None)
    (out / "blas-threads.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "blas-threads.md").write_text(md, encoding="utf-8")
    (out / "blas-threads.partial.json").unlink(missing_ok=True)
    print("saved docs/footprint/blas-threads.json and .md")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)          # the 1.4 GB snapshot and row captures
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", nargs="+", default=["default", "1", "2", "4"])
    ap.add_argument("--skip-models", action="store_true")
    ap.add_argument("--child", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.child:
        r = child(args.child, args.skip_models)
        print(MARK + json.dumps(r, default=str), flush=True)
        os._exit(0)                      # background threads from app imports must not linger
    sys.exit(parent(args.threads, args.skip_models))


if __name__ == "__main__":
    main()
