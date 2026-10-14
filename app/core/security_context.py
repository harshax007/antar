"""
Antar - the security context of a call
======================================
One object that says, for the request in hand: who is asking, in which role, under which
call chain. It is set once at the edge and travels with the request - into the agents it
runs, the traces it writes and the audit row it leaves - so "who authorised this, and
what did policy decide" is answered from one id instead of being pieced together.

After SMCP (Hou et al., arXiv 2602.01129, section 4.3): a unified security context
propagated through every invocation, on which policy and audit both rest.

    call_chain_id    one id per request; on the audit row, the response header
                     (x-call-chain-id) and every agent run inside it
    officer, role    from the verified token, never from the request body
    origin           "request" (an officer) or "system" (the autonomous loop, start-up)
    decisions        what policy decided for each agent run in this call
    trace_ids        the traces opened in this call, so the audit row points at the rows
                     and the query behind an answer

A context variable carries it, so it follows the request into worker threads and tasks
started from it. Code that runs with no context (a script, a test calling an agent
directly) is not refused: it is counted as unbound (`policy.counters()`), because a
refusal there would break the offline tools without protecting anything an HTTP caller
can reach - every HTTP request has a context.
"""
from __future__ import annotations

import contextlib
import contextvars
import uuid
from dataclasses import dataclass, field

_var: contextvars.ContextVar["SecurityContext | None"] = contextvars.ContextVar("antar_security_context", default=None)


@dataclass
class SecurityContext:
    officer: str
    role: str
    call_chain_id: str = field(default_factory=lambda: f"cc-{uuid.uuid4().hex[:16]}")
    origin: str = "request"                # request | system
    session_id: str = ""
    posting: str = ""                      # the officer's district; "" = not recorded
    scope: dict | None = None              # set when case rows were limited to the posting
    policy_ref: str = "AGENTS.md"
    decisions: list[dict] = field(default_factory=list)
    trace_ids: list[str] = field(default_factory=list)

    def note_decision(self, agent: str, outcome: str, reason: str = "", obligations: tuple = ()) -> None:
        if len(self.decisions) < 40:       # one request runs a handful of agents
            d = {"agent": agent, "outcome": outcome}
            if reason:
                d["reason"] = reason
            if obligations:
                d["obligations"] = list(obligations)
            self.decisions.append(d)

    def note_trace(self, trace_id: str | None) -> None:
        if trace_id and trace_id not in self.trace_ids and len(self.trace_ids) < 8:
            self.trace_ids.append(trace_id)

    def for_audit(self) -> dict:
        """What goes on the tamper-evident row. Ids and decisions; never case text."""
        out = {"call_chain_id": self.call_chain_id}
        if self.trace_ids:
            out["trace_ids"] = list(self.trace_ids)
        if self.decisions:
            out["policy"] = list(self.decisions)
        if self.scope:
            out["scope"] = dict(self.scope)
        return out


def current() -> SecurityContext | None:
    return _var.get()


def begin(officer: str, role: str, *, origin: str = "request", session_id: str = "", posting: str = ""):
    """Bind a context for the work that follows. Returns (context, token); pass the token
    to `end`."""
    ctx = SecurityContext(officer=officer or "anonymous", role=role or "none", origin=origin,
                          session_id=session_id, posting=posting or "")
    return ctx, _var.set(ctx)


def end(token) -> None:
    try:
        _var.reset(token)
    except ValueError:                     # reset from another context: leave it to be collected
        pass


@contextlib.contextmanager
def system(label: str):
    """Work the system starts by itself - the autonomous loop, a start-up warm-up. Named,
    so the audit trail says which, and marked as system so it is never mistaken for an
    officer."""
    ctx, token = begin(f"system:{label}", "system", origin="system")
    try:
        yield ctx
    finally:
        end(token)
