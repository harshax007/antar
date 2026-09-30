"""
Antar — footprint meter (final_backend.md §4 step 1).

Measures what the backend costs in disk and RAM, so every later change in the 2 GB plan
is judged against numbers rather than impressions. Additive and diagnostic only: the
database is opened read-only, nothing in the app is modified.

    python scripts/measure_footprint.py                     # disk + RAM, print report
    python scripts/measure_footprint.py --label baseline    # also save docs/footprint/baseline.{json,md}
    python scripts/measure_footprint.py --disk-only         # skip the in-process warm-up
    python scripts/measure_footprint.py --pid 1234          # RSS of an already running backend
    python scripts/measure_footprint.py --compare docs/footprint/baseline.json

RAM mode runs `main.background_warmup()` in this process — the exact code the server
runs at startup, so it costs what one backend start costs (the forecast store and caches
it refreshes are the same writes a normal start makes). Every line the warm-up prints is
stamped with the process RSS at that moment, which gives the cost of each stage without
duplicating any startup logic here. The QuickML warm-up is skipped by default (it is a
network call to an external model and costs no local RAM); pass --with-llm to include it.
Do not run this at the same time as the test suite (see PROGRESS.md §7).
"""

from __future__ import annotations

import os

# Same offline-first rule as main.py, and it must run before ANY import that could pull in
# huggingface_hub: the hub decides online/offline once, at import time. An earlier version
# of this script imported huggingface_hub before `import main`, so the reranker load went
# online and fetched a duplicate 88 MB revision into the cache. A meter must not change
# what it measures.
if os.getenv("ANTAR_BRAIN_ONLINE") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import argparse
import asyncio
import builtins
import json
import re
import sys
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
MB = 1024 * 1024
BUDGET_MB = 2048
APPSAIL_DEFAULT = {"ram_mb": 512, "disk_mb": 256}   # Catalyst AppSail defaults (final_backend.md §1)

# Tables the backend rebuilds at startup (PROGRESS.md "Deploy packaging must drop the
# derived forecast tables"). Counted separately: they need not ship in the artefact.
DERIVED_TABLES = {"forecast_cube", "geo_units", "forecast_meta", "forecast_output",
                  "forecast_models"}


def _mb(n: float) -> float:
    return round(n / MB, 1)


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total


# ── Disk ──────────────────────────────────────────────────────────────────────

def measure_database(db_path: Path) -> dict:
    import sqlite3

    out: dict = {"path": str(db_path)}
    for suffix in ("", "-wal", "-shm", ".gz"):
        p = Path(str(db_path) + suffix)
        # The deploy artefact lives in the repo even when ANTAR_DB points elsewhere (it
        # does since the database was rebuilt onto fresh sectors), so fall back to the
        # repo copy rather than reporting 0 MB and quietly shrinking the disk total.
        if suffix == ".gz" and not p.exists():
            p = ROOT / "main.db.gz"
        out["file" + (suffix.replace(".", "_").replace("-", "_") or "") + "_mb"] = (
            _mb(p.stat().st_size) if p.exists() else None)
    if not db_path.exists() or db_path.stat().st_size == 0:
        out["error"] = "database missing or empty"
        return out

    t0 = time.time()
    con = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        page_size = con.execute("PRAGMA page_size").fetchone()[0]
        page_count = con.execute("PRAGMA page_count").fetchone()[0]
        freelist = con.execute("PRAGMA freelist_count").fetchone()[0]
        kinds = {name: (typ, tbl) for typ, name, tbl in
                 con.execute("SELECT type, name, tbl_name FROM sqlite_master")}
        try:
            rows = con.execute(
                "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name").fetchall()
        except sqlite3.OperationalError as e:        # SQLite built without DBSTAT
            rows = []
            out["dbstat_error"] = str(e)
        try:
            out["fir_rows"] = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        except sqlite3.Error:
            out["fir_rows"] = None
    finally:
        con.close()

    objects = []
    totals = {"table": 0, "index": 0, "derived_table": 0, "derived_index": 0, "other": 0}
    for name, size in rows:
        typ, tbl = kinds.get(name, ("other", name))
        if name.startswith("sqlite_autoindex_"):
            typ = "index"
        derived = tbl in DERIVED_TABLES
        bucket = ("derived_" + typ) if derived and typ in ("table", "index") else (
            typ if typ in totals else "other")
        totals[bucket] += size
        objects.append({"name": name, "type": typ, "table": tbl, "derived": derived,
                        "mb": _mb(size)})
    objects.sort(key=lambda o: o["mb"], reverse=True)

    out.update({
        "page_size": page_size,
        "pages": page_count,
        "freelist_mb": _mb(freelist * page_size),
        "tables_mb": _mb(totals["table"]),
        "indexes_mb": _mb(totals["index"]),
        "derived_tables_mb": _mb(totals["derived_table"]),
        "derived_indexes_mb": _mb(totals["derived_index"]),
        "other_mb": _mb(totals["other"]),
        # What a data-only artefact must carry: the base tables, nothing rebuilt at start.
        "must_ship_mb": _mb(totals["table"]),
        "top_objects": objects[:25],
        "scan_seconds": round(time.time() - t0, 1),
    })
    return out


def _requirements(req_file: Path) -> list[str]:
    names = []
    for line in req_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9._-]+)", line)
        if m:
            names.append(m.group(1))
    return names


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def measure_packages(req_file: Path) -> dict:
    """Installed size of requirements.txt plus everything it pulls in (the deploy image)."""
    from importlib import metadata

    try:
        from packaging.markers import Marker
    except Exception:                                   # packaging absent → keep all deps
        Marker = None

    dists = {}
    for d in metadata.distributions():
        try:
            dists.setdefault(_norm(d.metadata["Name"]), d)
        except Exception:
            pass

    wanted = [_norm(n) for n in _requirements(req_file)]
    seen, missing, stack = set(), [], list(wanted)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        d = dists.get(name)
        if d is None:
            missing.append(name)
            continue
        for req in d.requires or []:
            spec, _, marker = req.partition(";")
            if marker.strip():
                if "extra" in marker:
                    continue
                if Marker is not None:
                    try:
                        if not Marker(marker.strip()).evaluate():
                            continue
                    except Exception:
                        pass
            m = re.match(r"^\s*([A-Za-z0-9._-]+)", spec)
            if m:
                stack.append(_norm(m.group(1)))

    sizes = []
    for name in seen:
        d = dists.get(name)
        if d is None:
            continue
        total = 0
        for f in d.files or []:
            try:
                total += os.path.getsize(d.locate_file(f))
            except OSError:
                pass
        sizes.append({"name": name, "version": d.version, "mb": _mb(total),
                      "direct": name in wanted})
    sizes.sort(key=lambda s: s["mb"], reverse=True)
    ml = {"torch", "transformers", "sentence-transformers", "tokenizers", "safetensors",
          "huggingface-hub", "sympy", "networkx", "scikit-learn", "scipy"}
    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "count": len(sizes),
        "total_mb": round(sum(s["mb"] for s in sizes), 1),
        "torch_stack_mb": round(sum(s["mb"] for s in sizes if s["name"] in
                                    {"torch", "transformers", "sentence-transformers",
                                     "tokenizers", "safetensors", "sympy"}), 1),
        "top": sizes[:20],
        "missing": sorted(set(missing)),
        "_ml_names": sorted(ml),
    }


def measure_models() -> dict:
    from app.core.settings import settings
    try:
        from app.second_brain.reranker import _CROSS_ENCODER_MODEL as cross
    except Exception:
        cross = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    try:
        from huggingface_hub import constants
        hub = Path(constants.HF_HUB_CACHE)
    except Exception:
        hub = Path.home() / ".cache" / "huggingface" / "hub"
    out = {"hub_cache": str(hub), "models": [], "unused_cached": []}
    used = set()
    for role, repo in (("embedder", settings.BRAIN_EMBEDDING_MODEL), ("reranker", cross)):
        # sentence-transformers resolves a bare name ("all-MiniLM-L6-v2") to its own org.
        candidates = [repo] if "/" in repo else [repo, "sentence-transformers/" + repo]
        p = next((hub / ("models--" + c.replace("/", "--")) for c in candidates
                  if (hub / ("models--" + c.replace("/", "--"))).exists()), None)
        if p is not None:
            used.add(p.name)
        out["models"].append({"role": role, "repo": repo, "cached": p is not None,
                              "dir": p.name if p else None,
                              "snapshots": len(list((p / "snapshots").iterdir()))
                              if p and (p / "snapshots").exists() else 0,
                              "mb": _mb(_dir_size(p)) if p else 0.0})
    if hub.exists():
        for d in sorted(hub.glob("models--*")):
            if d.name not in used:
                out["unused_cached"].append({"dir": d.name, "mb": _mb(_dir_size(d))})
    # Only what the backend loads counts toward the deploy footprint.
    out["total_mb"] = round(sum(m["mb"] for m in out["models"]), 1)
    return out


def measure_code() -> dict:
    return {"app_mb": _mb(_dir_size(ROOT / "app")),
            "main_py_kb": round((ROOT / "main.py").stat().st_size / 1024, 1)}


# ── RAM ───────────────────────────────────────────────────────────────────────

def _proc_mem(proc) -> dict:
    mi = proc.memory_info()
    out = {"rss_mb": _mb(mi.rss)}
    # Windows reports the working set as RSS, which the OS trims under pressure; private
    # (committed) bytes are what the process actually holds, so record both.
    if getattr(mi, "private", None):
        out["private_mb"] = _mb(mi.private)
    peak = getattr(mi, "peak_wset", None)               # Windows
    if peak is None:
        try:
            import resource                             # Linux: ru_maxrss is KiB
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        except Exception:
            peak = None
    out["peak_mb"] = _mb(peak) if peak else None
    return out


def measure_ram_inprocess(with_llm: bool) -> dict:
    import psutil

    if not with_llm:
        # DEMO_MODE only gates LLM use (settings.py L75; main.py `_llm_on`), so this skips
        # the external QuickML warm-up and nothing else.
        os.environ["DEMO_MODE"] = "true"
    os.chdir(ROOT)
    proc = psutil.Process()
    marks: list[dict] = []
    t0 = time.time()

    def mark(label: str) -> None:
        m = _proc_mem(proc)
        m.update({"t": round(time.time() - t0, 1), "label": label[:110]})
        marks.append(m)

    mark("python started")
    import main as antar_main                            # FastAPI app + every router
    mark("import main (app + all routers)")

    real_print = builtins.print

    def stamped_print(*args, **kwargs):
        target = kwargs.get("file")
        if target is None or target is sys.stdout:
            text = " ".join(str(a) for a in args).strip()
            if text:
                mark(text)
                real_print(f"[{marks[-1]['rss_mb']:>7.1f} MB] {text}",
                           **{k: v for k, v in kwargs.items() if k != "file"})
                return
        real_print(*args, **kwargs)

    builtins.print = stamped_print
    try:
        asyncio.run(antar_main.background_warmup())
    finally:
        builtins.print = real_print
    mark("warm-up returned")

    time.sleep(2)
    final = _proc_mem(proc)
    try:
        final["uss_mb"] = _mb(proc.memory_full_info().uss)
    except Exception:
        final["uss_mb"] = None

    stages = []
    for prev, cur in zip(marks, marks[1:]):
        stages.append({"label": cur["label"], "delta_mb": round(cur["rss_mb"] - prev["rss_mb"], 1),
                       "rss_mb": cur["rss_mb"], "t": cur["t"]})
    return {
        "mode": "in-process warm-up",
        "with_llm": with_llm,
        "seconds": round(time.time() - t0, 1),
        "final": final,
        "import_main_mb": marks[1]["rss_mb"] if len(marks) > 1 else None,
        "largest_stages": sorted(stages, key=lambda s: s["delta_mb"], reverse=True)[:12],
        "timeline": marks,
    }


def measure_ram_pid(pid: int) -> dict:
    import psutil

    proc = psutil.Process(pid)
    procs = [proc] + proc.children(recursive=True)
    rows = []
    for p in procs:
        try:
            mi = p.memory_info()
            rows.append({"pid": p.pid, "name": p.name(), "rss_mb": _mb(mi.rss),
                         "private_mb": _mb(getattr(mi, "private", 0)) or None,
                         "peak_mb": _mb(getattr(mi, "peak_wset", 0)) or None,
                         "uptime_min": round((time.time() - p.create_time()) / 60)})
        except psutil.Error:
            pass
    return {"mode": f"running process {pid}", "processes": rows,
            "final": {"rss_mb": round(sum(r["rss_mb"] for r in rows), 1),
                      "private_mb": round(sum(r["private_mb"] or 0 for r in rows), 1) or None,
                      "peak_mb": max((r["peak_mb"] or 0 for r in rows), default=None)}}


# ── Report ────────────────────────────────────────────────────────────────────

def verdict(report: dict) -> dict:
    db = report.get("database", {})
    disk = {
        "db_on_disk_mb": db.get("file_mb") or 0,
        "db_gz_mb": db.get("file_gz_mb") or 0,
        "packages_mb": report.get("packages", {}).get("total_mb", 0),
        "models_mb": report.get("models", {}).get("total_mb", 0),
        "code_mb": report.get("code", {}).get("app_mb", 0),
    }
    disk["total_mb"] = round(sum(disk.values()), 1)
    out = {"disk": disk}
    ram = report.get("ram", {}).get("final", {})
    seen = [v for v in (ram.get("peak_mb"), ram.get("private_mb"), ram.get("rss_mb")) if v]
    ram_peak = max(seen) if seen else None
    for tier, ram_cap, disk_cap in (("budget_2gb", BUDGET_MB, BUDGET_MB),
                                    ("appsail_default", APPSAIL_DEFAULT["ram_mb"],
                                     APPSAIL_DEFAULT["disk_mb"])):
        out[tier] = {
            "disk": "PASS" if disk["total_mb"] <= disk_cap else f"OVER by {disk['total_mb'] - disk_cap:.0f} MB",
            "ram": (None if ram_peak is None else
                    "PASS" if ram_peak <= ram_cap else f"OVER by {ram_peak - ram_cap:.0f} MB"),
        }
    return out


def to_markdown(r: dict) -> str:
    L = [f"# Antar footprint — {r['label']}", "",
         f"Measured {r['measured_at']} on `{r['host']}` · Python {r['packages'].get('python')}",
         "Generated by `scripts/measure_footprint.py` — do not edit by hand.", ""]
    v = r["verdict"]
    L += ["## Verdict", "",
          "| | Disk | RAM (peak) |", "|---|---|---|",
          f"| 2 GB budget | {v['budget_2gb']['disk']} | {v['budget_2gb']['ram'] or 'not measured'} |",
          f"| AppSail default (512 MB / 256 MB) | {v['appsail_default']['disk']} | "
          f"{v['appsail_default']['ram'] or 'not measured'} |", ""]
    d = v["disk"]
    L += ["## Disk", "", "| Item | MB |", "|---|---|",
          f"| `main.db` on disk | {d['db_on_disk_mb']} |",
          f"| `main.db.gz` artefact | {d['db_gz_mb']} |",
          f"| Python packages (requirements.txt closure) | {d['packages_mb']} |",
          f"| Model cache (embedder + reranker) | {d['models_mb']} |",
          f"| `app/` code | {d['code_mb']} |",
          f"| **Total** | **{d['total_mb']}** |", ""]
    db = r["database"]
    if "tables_mb" in db:
        L += ["### Inside `main.db`", "", "| Part | MB |", "|---|---|",
              f"| Base tables (must ship) | {db['tables_mb']} |",
              f"| Indexes (rebuilt at startup) | {db['indexes_mb']} |",
              f"| Derived forecast tables (rebuilt at startup) | {db['derived_tables_mb']} |",
              f"| Derived forecast indexes | {db['derived_indexes_mb']} |",
              f"| Free pages (reclaimable by VACUUM) | {db['freelist_mb']} |",
              f"| FIR rows | {db.get('fir_rows')} |", "",
              "Largest objects:", "", "| Object | Type | MB |", "|---|---|---|"]
        L += [f"| `{o['name']}` | {o['type']}{' (derived)' if o['derived'] else ''} | {o['mb']} |"
              for o in db["top_objects"][:15]]
        L.append("")
    m = r["models"]
    L += ["### Models the backend loads", "", "| Role | Configured | Cache dir | Snapshots | MB |",
          "|---|---|---|---|---|"]
    L += [f"| {x['role']} | `{x['repo']}` | `{x['dir']}` | {x['snapshots']} | {x['mb']} |"
          for x in m["models"]]
    if m.get("unused_cached"):
        L += ["", "Also in the cache but not loaded (not counted): " +
              ", ".join(f"`{u['dir']}` ({u['mb']} MB)" for u in m["unused_cached"])]
    if "cache_changed_during_run" in m:
        L += ["", "Model cache unchanged during the warm-up: " +
              ("**NO — investigate**" if m["cache_changed_during_run"] else "yes")]
    L.append("")
    p = r["packages"]
    L += ["### Largest installed packages", "", "| Package | Version | MB |", "|---|---|---|"]
    L += [f"| {s['name']}{'' if s['direct'] else ' (transitive)'} | {s['version']} | {s['mb']} |"
          for s in p["top"][:15]]
    L += ["", f"torch stack (torch, transformers, sentence-transformers, tokenizers, safetensors, "
              f"sympy): **{p['torch_stack_mb']} MB** of {p['total_mb']} MB.", ""]
    ram = r.get("ram")
    if ram:
        f = ram["final"]
        L += ["## RAM", "", f"Mode: {ram['mode']} · {ram.get('seconds', '—')} s", "",
              f"- Now: **{f.get('rss_mb')} MB RSS** (working set), private "
              f"{f.get('private_mb', '—')} MB, peak {f.get('peak_mb')} MB, "
              f"USS {f.get('uss_mb', '—')} MB",
              f"- After `import main` alone: {ram.get('import_main_mb')} MB", ""]
        if ram.get("largest_stages"):
            L += ["Largest steps (RSS growth between consecutive startup log lines):", "",
                  "| Δ MB | RSS MB | t (s) | Log line |", "|---|---|---|---|"]
            L += [f"| {s['delta_mb']} | {s['rss_mb']} | {s['t']} | {s['label'].replace('|', '/')} |"
                  for s in ram["largest_stages"]]
            L.append("")
    return NL.join(L) + NL


def compare(old: dict, new: dict) -> list[str]:
    pairs = [
        ("disk total MB", old["verdict"]["disk"]["total_mb"], new["verdict"]["disk"]["total_mb"]),
        ("main.db MB", old["verdict"]["disk"]["db_on_disk_mb"], new["verdict"]["disk"]["db_on_disk_mb"]),
        ("main.db.gz MB", old["verdict"]["disk"]["db_gz_mb"], new["verdict"]["disk"]["db_gz_mb"]),
        ("packages MB", old["verdict"]["disk"]["packages_mb"], new["verdict"]["disk"]["packages_mb"]),
        ("RSS after warm-up MB", (old.get("ram") or {}).get("final", {}).get("rss_mb"),
         (new.get("ram") or {}).get("final", {}).get("rss_mb")),
        ("peak RSS MB", (old.get("ram") or {}).get("final", {}).get("peak_mb"),
         (new.get("ram") or {}).get("final", {}).get("peak_mb")),
    ]
    lines = [f"Compared with {old['label']} ({old['measured_at']}):"]
    for name, a, b in pairs:
        if a is None or b is None:
            lines.append(f"  {name:<22} {a} -> {b}")
        else:
            lines.append(f"  {name:<22} {a:>9.1f} -> {b:>9.1f}   ({b - a:+.1f})")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split(NL + NL)[0])
    ap.add_argument("--label", help="save docs/footprint/<label>.json and .md")
    ap.add_argument("--disk-only", action="store_true", help="skip the RAM measurement")
    ap.add_argument("--pid", type=int, help="measure a running backend instead of warming up here")
    ap.add_argument("--with-llm", action="store_true", help="include the QuickML network warm-up")
    ap.add_argument("--compare", help="a previous report .json to diff against")
    args = ap.parse_args()

    from app.core.db_path import DB_PATH
    import platform

    report = {
        "label": args.label or "adhoc",
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "host": platform.node(),
        "database": measure_database(Path(DB_PATH)),
        "packages": measure_packages(ROOT / "requirements.txt"),
        "models": measure_models(),
        "code": measure_code(),
    }
    if args.pid:
        report["ram"] = measure_ram_pid(args.pid)
    elif not args.disk_only:
        report["ram"] = measure_ram_inprocess(args.with_llm)
        # Guard: the warm-up must not have downloaded anything into the model cache.
        after = measure_models()
        report["models"]["cache_changed_during_run"] = (
            [m["mb"] for m in after["models"]] != [m["mb"] for m in report["models"]["models"]])
        if report["models"]["cache_changed_during_run"]:
            print("WARNING: the model cache changed during the warm-up — something went "
                  "online. Numbers are still recorded; investigate before trusting them.")
    report["packages"].pop("_ml_names", None)
    report["verdict"] = verdict(report)

    md = to_markdown(report)
    print()
    print(md)
    if args.compare:
        print(NL.join(compare(json.loads(Path(args.compare).read_text(encoding="utf-8")), report)))
    if args.label:
        out_dir = ROOT / "docs" / "footprint"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{args.label}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (out_dir / f"{args.label}.md").write_text(md, encoding="utf-8")
        print(f"saved docs/footprint/{args.label}.json and .md")
    sys.stdout.flush()
    # The warm-up leaves the orchestrator / forecast threads behind; they must not keep a
    # measuring process alive after the report is written.
    os._exit(0)


if __name__ == "__main__":
    main()
