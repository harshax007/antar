"""
Antar — export a clean, runnable copy of the backend.

    python scripts/make_clean_copy.py --dest D:/Project
    python scripts/make_clean_copy.py --dest D:/Project --with-frontend --force

Copies what is needed to RUN and VERIFY the system, and nothing else. Written because the
repository lives on a drive that is losing files (final_backend.md §3.2) and because a
1,441-file working directory with build caches, backups and a 1.4 GB damaged database is
not what anyone should hand over.

What it takes:
  * the backend package, entry points, requirements, Docker and Catalyst config
  * scripts/ and tests/ — a copy you cannot verify is not a deliverable
  * docs/ — the plan, the measured footprints, the forecast back-test, the model card
  * models/onnx/ — the exported Brain models, so it runs without torch
  * the databases it actually reads: the REBUILT main.db and the Brain corpus

What it leaves behind, deliberately:
  * `main.db` in the repo root — the copy with unreadable sectors
  * node_modules, .next, __pycache__, .pytest_cache, .venv, .git
  * *.bak, *.gz.prev, main.db.pre1m.bak, data_sessions/ scratch, graphify-out/

It then rewrites `.env` so every path points inside the destination: the copy must not
reach back to the failing drive to find its data.
"""

from __future__ import annotations

import argparse
import os
import shutil
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

# Directories copied whole, minus the excludes below.
DIRS = ["app", "scripts", "tests", "docs", "knowledge", "models/onnx"]
FRONTEND_DIRS = ["antar-frontend"]

FILES = ["main.py", "run.py", "requirements.txt", "requirements-runtime.txt",
         "Dockerfile", "Dockerfile.onnx", ".dockerignore", "app-config.json",
         "catalyst.json", "pytest.ini", "AGENTS.md", "PROGRESS.md", "RUN.md",
         "final_backend.md", ".env.example"]

EXCLUDE_DIRS = {"node_modules", ".next", "__pycache__", ".pytest_cache", ".venv", "venv",
                ".hypothesis",
                ".git", ".mypy_cache", ".ruff_cache", "graphify-out", "data_sessions",
                ".claude"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".bak", ".log", ".gz.prev")


def _ignore(_dir, names):
    out = set()
    for n in names:
        if n in EXCLUDE_DIRS or n.endswith(EXCLUDE_SUFFIX):
            out.add(n)
    return out


def _drop_failed_int8(dest: Path) -> tuple[int, int]:
    """Remove int8 ONNX weights whose own meta.json records a parity FAILURE.

    The int8 export missed its 0.995 cosine gate (0.990 at best), so `onnx_backend`
    refuses to load it — `variant="auto"` consults `meta["parity"]["int8"]["pass"]`, not
    the file's existence. A 57 MB weight file that the loader will never choose is not a
    file required to run the code. The fp32 weights, which ship at cosine 1.0, stay.
    """
    import json

    n = b = 0
    for meta_path in (dest / "models" / "onnx").glob("*/meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("parity", {}).get("int8", {}).get("pass"):
            continue
        name = meta.get("files", {}).get("int8")
        f = meta_path.parent / name if name else None
        if f and f.exists():
            b += f.stat().st_size
            f.unlink()
            n += 1
    return n, b


def _copy_tree(src: Path, dst: Path) -> tuple[int, int]:
    if not src.exists():
        return 0, 0
    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)
    files = [p for p in dst.rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)


def _env_for(dest: Path) -> str | None:
    """Rewrite the three path settings so the copy is self-contained.

    A copy whose .env still points at E:\\ would keep reading from the failing disk and
    look fine right up until it did not.
    """
    src = ROOT / ".env"
    if not src.exists():
        return None
    data = dest / "data"
    replacements = {
        "ANTAR_DB": str(data / "main.db"),
        "OBS_DIR": str(data / "obs"),
        "ANTAR_BRAIN_DB": str(data / "brain_vectors.db"),
    }
    out, seen = [], set()
    for line in src.read_text(encoding="utf-8").splitlines():
        key = line.split("=", 1)[0].strip()
        if key in replacements:
            out.append(f"{key}={replacements[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in replacements.items():
        if key not in seen:
            out.append(f"{key}={value}")
    return chr(10).join(out) + chr(10)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10) + chr(10))[0])
    ap.add_argument("--dest", required=True)
    ap.add_argument("--with-frontend", action="store_true",
                    help="include antar-frontend source (without node_modules/.next)")
    ap.add_argument("--no-data", action="store_true", help="code only, skip the databases")
    ap.add_argument("--force", action="store_true", help="overwrite a non-empty destination")
    args = ap.parse_args()

    dest = Path(args.dest)
    if dest.exists() and any(dest.iterdir()) and not args.force:
        print(f"{dest} is not empty — re-run with --force to overwrite")
        return 2
    dest.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    total_files = total_bytes = 0
    for rel in DIRS + (FRONTEND_DIRS if args.with_frontend else []):
        n, b = _copy_tree(ROOT / rel, dest / rel)
        total_files += n
        total_bytes += b
        print(f"  {rel:<24} {n:>6,} files  {b / 1048576:>8.1f} MB")

    dropped_n, dropped_b = _drop_failed_int8(dest)
    if dropped_n:
        total_files -= dropped_n
        total_bytes -= dropped_b
        print(f"  {'models/onnx int8':<24} {dropped_n} file(s) dropped "
              f"({dropped_b / 1048576:.1f} MB) — failed the parity gate, never loaded")

    for name in FILES:
        src = ROOT / name
        if src.exists():
            shutil.copyfile(src, dest / name)
            total_files += 1
            total_bytes += src.stat().st_size

    env = _env_for(dest)
    if env:
        (dest / ".env").write_text(env, encoding="utf-8")
        print(f"  {'.env':<24} rewritten to point inside {dest}")

    # ── the databases it actually reads ──
    if not args.no_data:
        from app.core.db_path import get_db_path
        from app.second_brain import vec_store

        data = dest / "data"
        data.mkdir(parents=True, exist_ok=True)
        for label, src in (("main.db", Path(get_db_path())),
                           ("brain_vectors.db", vec_store.store_path())):
            if not src.exists():
                print(f"  {label:<24} SKIPPED (not found at {src})")
                continue
            t = time.time()
            shutil.copyfile(src, data / label)
            size = (data / label).stat().st_size
            total_files += 1
            total_bytes += size
            print(f"  data/{label:<19} {size / 1048576:>8.1f} MB in {time.time() - t:.0f}s")

        # The packed memmap sidecars (.i8/.ids/.mult) beside brain_vectors.db. Without
        # them the copy still works — pack() rebuilds on first search — but the first
        # query would pay a full re-pack instead of 110 ms.
        for src in vec_store.store_path().parent.glob(
                vec_store.store_path().stem + ".*"):
            if src.suffix in (".i8", ".ids", ".mult"):
                shutil.copyfile(src, data / ("brain_vectors" + src.suffix))
                total_files += 1
                total_bytes += src.stat().st_size
                print(f"  data/brain_vectors{src.suffix:<9} "
                      f"{src.stat().st_size / 1048576:>8.1f} MB")
        (data / "obs").mkdir(exist_ok=True)

    print()
    print(f"{total_files:,} files · {total_bytes / 1048576:.0f} MB · {time.time() - t0:.0f}s")
    print(f"clean copy at {dest}")
    print()
    print("to run it:")
    print(f"  cd {dest}")
    print("  pip install -r requirements.txt        # or requirements-runtime.txt (no torch)")
    print("  python -m uvicorn main:app --port 8000")
    print("  python -m pytest -q")
    return 0


if __name__ == "__main__":
    sys.exit(main())
