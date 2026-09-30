"""
requirements-runtime.txt must not drift from requirements.txt.

The serving image installs requirements-runtime.txt (torch-free, ONNX Brain); everything
else — dev, CI, the export builder — installs requirements.txt. Two files listing the
same libraries at different versions is how a container ends up behaving unlike every
environment it was tested in, so this pins the relationship:

  * shared packages carry identical versions
  * the runtime file really does exclude the torch stack
  * it really does include what the ONNX backend imports
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TORCH_STACK = {"torch", "sentence-transformers", "transformers", "safetensors", "sympy"}
ONNX_RUNTIME_NEEDS = {"onnxruntime", "tokenizers", "numpy"}


def _pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9._-]+)\s*==\s*([A-Za-z0-9._+-]+)$", line)
        if m:
            pins[m.group(1).lower()] = m.group(2)
    return pins


def test_shared_packages_have_identical_pins():
    dev = _pins(ROOT / "requirements.txt")
    runtime = _pins(ROOT / "requirements-runtime.txt")
    drifted = {name: (dev[name], runtime[name])
               for name in set(dev) & set(runtime) if dev[name] != runtime[name]}
    assert not drifted, (
        "requirements-runtime.txt disagrees with requirements.txt on: " +
        ", ".join(f"{n} (dev {d} vs runtime {r})" for n, (d, r) in drifted.items()))


def test_runtime_excludes_the_torch_stack():
    """The entire point of the file: 681 MB of framework the serving image does not need."""
    runtime = _pins(ROOT / "requirements-runtime.txt")
    present = TORCH_STACK & set(runtime)
    assert not present, (
        f"requirements-runtime.txt still pulls {sorted(present)} — the ONNX backend exists "
        f"so the serving image does not have to")


def test_runtime_includes_what_the_onnx_backend_imports():
    runtime = _pins(ROOT / "requirements-runtime.txt")
    missing = ONNX_RUNTIME_NEEDS - set(runtime)
    assert not missing, f"requirements-runtime.txt is missing {sorted(missing)}"


def test_dev_requirements_still_provide_the_exporter():
    """scripts/export_onnx_models.py needs sentence-transformers to produce and verify
    the artifacts, so the dev/build spec must keep it."""
    dev = _pins(ROOT / "requirements.txt")
    assert "sentence-transformers" in dev, (
        "requirements.txt lost sentence-transformers — the ONNX export and its parity "
        "check are built on it, and torch is the only reference the check has")
