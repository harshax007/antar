"""
Antar - pin what runs
=====================
AGENTS.md says which agents exist. This says which VERSION of each was reviewed: a SHA-256
of every agent's module and of every system prompt, written to `agents.lock.json` by

    python scripts/lock_agents.py

and compared at start-up and in the test suite. A module or a prompt that changed without
being re-locked is named. In development that is a warning and a failing test; in
production the server refuses to start, because a changed prompt is a changed policy.

After SMCP (arXiv 2602.01129, section 4.1): a registry keeps provenance and version history
so a component that was trusted yesterday and altered today is noticed ("rug pull").

Line endings are normalised before hashing, so a checkout on Windows and one on Linux
agree. The short hash of all prompts together is the `prompt_version` stamped on every
trace, which ties an answer to the exact instructions that produced it.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCK = ROOT / "agents.lock.json"


def _sha(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _prompts() -> dict[str, str]:
    """Every system prompt a model can be given, by name."""
    from app.agents import intent_parser, query_agent
    from app.core import antar_identity, rag_security
    from app.obs import judge
    out = {
        "select": query_agent.SELECT_SYSTEM,
        "compose": query_agent.COMPOSE_SYSTEM,
        "intent": intent_parser._PARSE_SYSTEM,
        "judge": judge._JUDGE_SYSTEM,
        "untrusted_data_policy": rag_security.UNTRUSTED_POLICY,
    }
    for task in ("answer", "synthesis"):
        for lang in ("en", "kn"):
            out[f"identity:{task}:{lang}"] = antar_identity.system_prompt(task, lang)
    return out


def compute() -> dict:
    from app.agents import manifest
    modules = {}
    for a in manifest.load().agents.values():
        path = a.module.split("::", 1)[0]
        f = ROOT / path
        modules[a.agent] = {"path": path, "sha256": _sha(f.read_text(encoding="utf-8")) if f.exists() else None}
    prompts = {k: _sha(v) for k, v in _prompts().items()}
    version = hashlib.sha256("".join(f"{k}={v};" for k, v in sorted(prompts.items())).encode()).hexdigest()[:12]
    return {"modules": modules, "prompts": prompts, "prompt_version": version}


def read_lock() -> dict | None:
    try:
        return json.loads(LOCK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_lock() -> dict:
    now = compute()
    LOCK.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return now


def status() -> dict:
    """What differs between what is running and what was locked."""
    lock = read_lock()
    try:
        now = compute()
    except Exception as e:                         # never let the check itself stop a start-up in dev
        return {"locked": lock is not None, "ok": False, "error": type(e).__name__, "changed": [], "prompt_version": None}
    if lock is None:
        return {"locked": False, "ok": False, "changed": [], "prompt_version": now["prompt_version"],
                "note": "no agents.lock.json: run python scripts/lock_agents.py"}
    changed = []
    for name, m in now["modules"].items():
        was = (lock.get("modules") or {}).get(name)
        if was is None:
            changed.append(f"agent {name}: not in the lock")
        elif was.get("sha256") != m["sha256"]:
            changed.append(f"agent {name}: {m['path']} changed")
    for name in (lock.get("modules") or {}):
        if name not in now["modules"]:
            changed.append(f"agent {name}: locked but no longer declared")
    for name, h in now["prompts"].items():
        if (lock.get("prompts") or {}).get(name) != h:
            changed.append(f"prompt {name} changed")
    return {"locked": True, "ok": not changed, "changed": changed,
            "prompt_version": now["prompt_version"], "locked_prompt_version": lock.get("prompt_version")}


_version: str | None = None


def prompt_version() -> str:
    """The short hash of all system prompts, for stamping on a trace. Computed once."""
    global _version
    if _version is None:
        try:
            _version = compute()["prompt_version"]
        except Exception:
            _version = "unknown"
    return _version


def enforce(production: bool) -> dict:
    """Start-up check. Raises in production when something changed since it was locked."""
    st = status()
    if not st["ok"] and production:
        raise RuntimeError("agents or prompts differ from agents.lock.json: "
                           + "; ".join(st.get("changed") or [st.get("note") or st.get("error") or "unknown"])[:400])
    return st
