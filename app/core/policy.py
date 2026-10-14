"""
Antar - one policy decision point
=================================
Who may run which agent, and on what conditions, decided in one function from what
AGENTS.md declares beside each agent:

    sensitivity   aggregate | case | person | external     what the agent's output is about
    min_role      the lowest role that may run it
    obligations   conditions the result must meet before it leaves the agent

`decide(ctx, agent)` returns PERMIT, DENY (with a reason an officer can read) or
PERMIT_WITH_OBLIGATIONS. `orchestrator.run_agent` asks it before the agent runs and applies
the obligations to what comes back, so a rule cannot be skipped by a route that forgot a
dependency, and an agent cannot return more than its declaration allows even if its own
code is changed to try.

After SMCP (arXiv 2602.01129, section 4.4): a policy decision point, with agents and
tools as enforcement points, and obligations such as masking and aggregation.

Routers keep their role dependencies; this is a second, independent check behind them.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from app.core.security_context import SecurityContext

PERMIT, DENY, PERMIT_WITH_OBLIGATIONS = "PERMIT", "DENY", "PERMIT_WITH_OBLIGATIONS"
SENSITIVITIES = ("aggregate", "case", "person", "external")
OBLIGATIONS = ("redact_pii", "aggregate_only", "label_unverified", "row_cap")

# keys that carry a person or a single case; an aggregate-only result may not hold them
_PERSON_KEYS = {"rows", "suspects", "suspect_ids", "persons", "accused_ids", "names", "fir_numbers"}

_lock = threading.Lock()
_counts = {"permit": 0, "deny": 0, "obligations": 0, "unbound": 0, "undeclared": 0}


@dataclass(frozen=True)
class Decision:
    outcome: str
    reason: str = ""
    obligations: tuple[str, ...] = ()

    @property
    def denied(self) -> bool:
        return self.outcome == DENY


def _bump(key: str) -> None:
    with _lock:
        _counts[key] += 1


def counters() -> dict:
    with _lock:
        return dict(_counts)


def _rank(role: str) -> int:
    from app.core.auth_middleware import _RANK
    return _RANK.get(role, -1)


def _agent_def(name: str):
    try:
        from app.agents import manifest
        agents = manifest.load().agents
    except Exception:
        return None
    a = agents.get(name)
    if a is None:
        a = next((x for x in agents.values() if name in x.aliases), None)
    return a


def decide(ctx: SecurityContext | None, agent: str) -> Decision:
    a = _agent_def(agent)
    if a is None or not getattr(a, "sensitivity", ""):
        # run under a name the manifest does not declare (a job wrapper): nothing to decide on
        _bump("undeclared")
        return Decision(PERMIT, "no declared policy")
    obligations = tuple(a.obligations)
    if ctx is None:
        _bump("unbound")
    elif ctx.origin != "system" and _rank(ctx.role) < _rank(a.min_role):
        _bump("deny")
        d = Decision(DENY, f"needs {a.min_role} or above (this is {a.sensitivity}-level data)")
        ctx.note_decision(agent, DENY, d.reason)
        return d
    if obligations:
        _bump("obligations")
        if ctx is not None:
            ctx.note_decision(agent, PERMIT_WITH_OBLIGATIONS, obligations=obligations)
        return Decision(PERMIT_WITH_OBLIGATIONS, obligations=obligations)
    _bump("permit")
    if ctx is not None:
        ctx.note_decision(agent, PERMIT)
    return Decision(PERMIT)


# ── obligations ──────────────────────────────────────────────────────────────

def _deep(obj, fn, depth: int = 0):
    if depth > 8:
        return obj
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, dict):
        return {k: _deep(v, fn, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep(v, fn, depth + 1) for v in obj]
    return obj


def _cap(obj, n: int, depth: int = 0):
    if depth > 8:
        return obj
    if isinstance(obj, list):
        return [_cap(v, n, depth + 1) for v in obj[:n]]
    if isinstance(obj, dict):
        return {k: _cap(v, n, depth + 1) for k, v in obj.items()}
    return obj


def apply_obligations(result, obligations: tuple[str, ...]):
    """Make a result meet its agent's declared conditions. Unknown obligations are ignored
    here and rejected when the manifest is loaded."""
    for ob in obligations:
        name, _, arg = ob.partition(":")
        if name == "redact_pii":
            from app.core.guardrails import redact_pii
            result = _deep(result, redact_pii)
        elif name == "aggregate_only" and isinstance(result, dict):
            result = {k: v for k, v in result.items() if k not in _PERSON_KEYS}
        elif name == "label_unverified" and isinstance(result, dict):
            result = {**result, "unverified": True}
        elif name == "row_cap":
            try:
                result = _cap(result, max(1, int(arg or 100)))
            except ValueError:
                pass
    return result
