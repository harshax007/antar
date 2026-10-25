"""Run a forecast refit in a short-lived child process.

A refit holds the full weekly history of every unit and category in numpy arrays while it
fits 72 models. Inside the server that memory was never handed back: CPython keeps freed
arenas, so the process sat ~0.75 GB heavier after every refit and peaked ~1 GB above that
while it ran (measured 2026-10-25: 2.5 GB steady, 3.56 GB peak). Run in a child, the same
work returns every byte to the system when the child exits, and the server only reads the
rows the child wrote.

Only the refit moves out. Checking whether forecasts are current is a few small queries and
stays in-process, so a server whose forecasts are current never starts a child.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "@@RESULT "                       # the child's one machine-readable line on stdout


def emit(result) -> None:
    """Called in the child: hand the result back to the parent."""
    print(MARK + json.dumps(result, default=str), flush=True)


def run(module: str, *args: str, timeout: float = 900) -> dict:
    """`python -m module args...` with the server's environment; returns what it emitted."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([sys.executable, "-m", module, *args], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "").strip().splitlines()[-5:]
        raise RuntimeError(f"{module} exited {p.returncode}: " + " | ".join(tail))
    for line in reversed(p.stdout.splitlines()):
        if line.startswith(MARK):
            return json.loads(line[len(MARK):])
    raise RuntimeError(f"{module} returned no result")
