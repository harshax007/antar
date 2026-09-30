# BLAS thread cap — measurements

Measured 2026-09-22/23 on a 12-logical-CPU Windows laptop, Python 3.11.15, torch
2.13.0+cpu. Supports `final_backend.md` §4 step 2b and the cap installed at the top of
`main.py`.

**Status: partial.** `scripts/bench_blas_threads.py` measured `default` and `1`. The
`2` and `4` settings were not measured: the run was interrupted, and reruns then failed
because `main.db` sits on a drive with failing sectors (see "Why the run is incomplete").
The numbers below were enough to choose the value, because 1 thread is also what the
deployed container already runs.

## Why cap at all

numpy and scipy each bundle their own OpenBLAS, and OpenBLAS reserves a workspace per CPU
thread the first time it is imported. Import cost alone, nothing else running:

| Imports | Default (12 threads) | 1 thread |
|---|---|---|
| numpy | +365 MB private | +11 MB |
| scipy.linalg | +393 MB | +9 MB |
| pandas | +23 MB | +22 MB |
| scikit-learn | +49 MB | +50 MB |
| torch | +150 MB | +149 MB |
| **total** | **990 MB** | **251 MB** |

`OMP_NUM_THREADS=1` on its own is sufficient — OpenBLAS falls back to it when
`OPENBLAS_NUM_THREADS` is unset (verified: pools reported `[('openblas', 1)]`, 758 MB →
20 MB for numpy + scipy).

## What the cap costs

`scripts/bench_blas_threads.py`, one process per setting, forecast fit on the real-record
as-of (72 models, 257,345 rows), golden suite run twice (cold process, then warm):

| Threads | Forecast fit | Golden pass 1 (cold) | Golden pass 2 (warm) | Golden score | Private at end |
|---|---|---|---|---|---|
| default (12) | 75.0 s | 53.31 s | 12.03 s | 35/35 | 1,659 MB |
| 1 | 76.2 s | 61.53 s | 12.00 s | 35/35 | **875 MB** |
| 2 | not measured | | | | |
| 4 | not measured | | | | |

- Forecast fit: **+1.6%** at one thread. The fit is 72 small per-unit GLMs, not a few
  large matrix multiplications, so BLAS parallelism has little to work with.
- Warm query latency: **unchanged** (12.00 s vs 12.03 s for 35 queries). Queries are
  SQLite work; BLAS is not on that path.
- Cold pass 1 is dominated by per-process cache building, not threads, and is noisy
  (53 s and 62 s here; 488 s in an earlier run against a cold OS page cache).
- Correctness: **35/35 in both**, so the cap changes no answer.

## End-to-end effect of the committed change

`import main` in a subprocess, with and without the cap:

| | Private | RSS | Pools |
|---|---|---|---|
| Capped (new default) | **+164 MB** | 208 MB | openblas 1, openmp 1 |
| Uncapped (pre-change) | +903 MB | 208 MB | openblas 12, openmp 12 |

**−739 MB of reserved memory; RSS identical.** That distinction matters: this is memory
committed but never touched, so on a Linux container — which charges the cgroup for
resident pages — the saving is smaller than the headline. It is still the right default,
because it costs nothing measurable and matches what the deployed image already sets.

## Why the value is 1

The deployed container already sets `OMP_NUM_THREADS=1` (`Dockerfile` ENV and
`app-config.json`). Capping at 1 in `main.py` therefore changes **nothing** in
production; it makes local dev, tests and a deploy whose env var went missing behave the
way the container already does. An operator who sets any of the three variables keeps
full control (`tests/test_runtime_env.py::test_operator_override_wins`).

## Why the run is incomplete

Reruns for the 2 and 4 settings failed with `disk I/O error` while reading `main.db`.
Root cause is not software: `PRAGMA quick_check` reports an unreadable page (error 266 =
SQLITE_IOERR_READ) and Windows logged `disk` Event ID 7, *"The device
\Device\Harddisk0\DR0 has a bad block"*, at 03:44 on 2026-09-23 — the drive holding the
repo (`E:` = Disk 0, ST1000LM049 HDD) has failing sectors. Five 4 KiB pages around byte
1,352,183,808 cannot be read. They belong to `forecast_cube`, a derived table the backend
rebuilds at startup. All 1,000,000 FIR rows still read cleanly. See `final_backend.md`
§1.2.

The benchmark now takes a consistent snapshot via the SQLite backup API and recovers a
stale WAL index first, so it can be completed once the database is rebuilt onto good
sectors.
