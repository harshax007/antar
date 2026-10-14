"""
Antar — Agent Manifest Loader
=============================
Parses AGENTS.md (repo root) into the single source of truth for agent identity.

AGENTS.md is the authoritative document; this module is the reader. Three consumers
are generated from it, so they can no longer drift apart:

  • orchestrator.register_default_fleet()  — name / role / timeout / retries
  • supervisor._ROUTE_MAP                  — route label -> graph node
  • tests/test_agents_manifest.py          — fails the build on any disagreement

Why parse markdown instead of declaring this in Python? Because the value is that the
file a human reads IS the file the code reads. A Python dict would drift from its own
docstring within a sprint; that is exactly the failure this replaces.

Fail-open: a malformed AGENTS.md degrades to an empty manifest and the callers keep
their hardcoded fallbacks. A missing manifest must never take the chat down — the
drift *test* is what fails loudly, not the request path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "AGENTS.md"

# ```yaml … ``` blocks. Each parses to one agent, or to the single topology block.
_YAML_BLOCK = re.compile(r"^```yaml\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)

REQUIRED_FIELDS = ("agent", "kind", "role", "module")
VALID_KINDS = {"worker", "service", "system"}


@dataclass(frozen=True)
class AgentDef:
    """One agent, exactly as declared in AGENTS.md."""
    agent: str
    kind: str
    role: str
    module: str
    graph_node: str | None = None
    hosted_by: str | None = None
    unrouted_fallback: str | None = None
    hosts: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    timeout_s: float = 8.0
    retries: int = 1
    surfaces: tuple[str, ...] = ()
    reads: tuple[str, ...] = ()
    emits: tuple[str, ...] = ()
    guardrails: tuple[str, ...] = ()
    hitl: bool = False
    degraded: str = ""
    notes: str = ""
    # what policy decides on (app/core/policy.py)
    sensitivity: str = ""                  # aggregate | case | person | external
    min_role: str = "Constable"
    obligations: tuple[str, ...] = ()

    @property
    def dispatch_node(self) -> str | None:
        """The node a route addressed to this agent actually reaches.

        `graph_node` when the agent runs in the graph, otherwise `unrouted_fallback` —
        which absorbs the route WITHOUT running this agent. `reachable` distinguishes
        the two; callers that care about honesty should check it.
        """
        return self.graph_node or self.unrouted_fallback

    @property
    def reachable(self) -> bool:
        """True when a graph turn can actually execute this agent."""
        return self.graph_node is not None


@dataclass(frozen=True)
class Manifest:
    agents: dict[str, AgentDef] = field(default_factory=dict)
    topology: dict[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()

    # ── derived views ────────────────────────────────────────────────────────
    def route_map(self) -> dict[str, str]:
        """{ROUTE_LABEL: graph_node} — generated replacement for _ROUTE_MAP."""
        out: dict[str, str] = {}
        for a in self.agents.values():
            node = a.dispatch_node
            if not node:
                continue
            for r in a.routes:
                out[r.strip().upper()] = node
        return out

    def route_owner(self) -> dict[str, str]:
        """{ROUTE_LABEL: agent_id} — which agent a label is *addressed* to."""
        return {r.strip().upper(): a.agent for a in self.agents.values() for r in a.routes}

    def alias_map(self) -> dict[str, str]:
        """{alias: canonical_agent_id}, including each agent's own id."""
        out: dict[str, str] = {}
        for a in self.agents.values():
            out[a.agent] = a.agent
            for al in a.aliases:
                out[al.strip().lower()] = a.agent
        return out

    def graph_nodes(self) -> set[str]:
        """Every node in the compiled graph, entry node included."""
        return set(self.topology.get("nodes") or [])

    def dispatchable_nodes(self) -> set[str]:
        """Nodes route_fn is allowed to RETURN — the compiled set minus the entry node.

        Returning the entry node from a conditional edge would route the supervisor back
        into itself. This is the set the old hardcoded _GRAPH_NODES represented.
        """
        return self.graph_nodes() - {self.topology.get("entry")}

    def fleet(self) -> list[AgentDef]:
        """Agents the orchestrator registers (everything that does real work)."""
        return [a for a in self.agents.values() if a.kind in ("worker", "service")]

    def unreachable(self) -> list[AgentDef]:
        """Workers with routes that no graph node executes — the honest gap list."""
        return [a for a in self.agents.values()
                if a.kind == "worker" and not a.reachable and a.routes]

    def hitl_required(self) -> list[str]:
        return sorted(a.agent for a in self.agents.values() if a.hitl)

    def resolve(self, name: str) -> AgentDef | None:
        """Look up by canonical id, alias, or route label. Case-insensitive."""
        key = (name or "").strip()
        if not key:
            return None
        canon = self.alias_map().get(key.lower())
        if canon:
            return self.agents.get(canon)
        owner = self.route_owner().get(key.upper())
        return self.agents.get(owner) if owner else None


# ── unresolved-route telemetry ────────────────────────────────────────────────
# The bug this manifest exists to prevent was SILENT: an unrecognised label fell
# through to "query" and nobody found out for weeks. Unknown labels are now counted
# and logged, and surfaced at /api/orchestrator/status.
_unresolved: dict[str, int] = {}


def note_unresolved_route(label: str) -> None:
    key = (label or "?").strip().upper()
    _unresolved[key] = _unresolved.get(key, 0) + 1
    if _unresolved[key] == 1:          # log once per label per process, not per request
        logger.warning("route_label_unresolved", label=key,
                       hint="add it to AGENTS.md or remove the emitter")


def unresolved_routes() -> dict[str, int]:
    return dict(_unresolved)


def reset_unresolved() -> None:
    _unresolved.clear()


# ── parsing ───────────────────────────────────────────────────────────────────
def _tuple(v: Any) -> tuple[str, ...]:
    if v is None:
        return ()
    if isinstance(v, str):
        return (v,)
    return tuple(str(x) for x in v)


def _build_agent(d: dict, errors: list[str]) -> AgentDef | None:
    name = d.get("agent")
    for f in REQUIRED_FIELDS:
        if not d.get(f):
            errors.append(f"agent '{name or '?'}' is missing required field '{f}'")
            return None
    kind = str(d["kind"]).strip().lower()
    if kind not in VALID_KINDS:
        errors.append(f"agent '{name}' has invalid kind '{kind}' (expected one of {sorted(VALID_KINDS)})")
        return None
    sensitivity = str(d.get("sensitivity") or "").strip().lower()
    min_role = str(d.get("min_role") or "Constable").strip()
    obligations = _tuple(d.get("obligations"))
    from app.core import policy as _policy
    from app.core.auth_middleware import ROLES as _ROLES
    if sensitivity not in _policy.SENSITIVITIES:
        errors.append(f"agent '{name}' must declare sensitivity as one of {list(_policy.SENSITIVITIES)}")
        return None
    if min_role not in _ROLES:
        errors.append(f"agent '{name}' has an unknown min_role '{min_role}'")
        return None
    bad = [o for o in obligations if o.partition(":")[0] not in _policy.OBLIGATIONS]
    if bad:
        errors.append(f"agent '{name}' declares unknown obligations {bad}")
        return None
    try:
        return AgentDef(
            sensitivity=sensitivity, min_role=min_role, obligations=obligations,
            agent=str(name).strip().lower(),
            kind=kind,
            role=str(d["role"]).strip(),
            module=str(d["module"]).strip(),
            graph_node=(str(d["graph_node"]).strip() if d.get("graph_node") else None),
            hosted_by=(str(d["hosted_by"]).strip() if d.get("hosted_by") else None),
            unrouted_fallback=(str(d["unrouted_fallback"]).strip() if d.get("unrouted_fallback") else None),
            hosts=_tuple(d.get("hosts")),
            aliases=_tuple(d.get("aliases")),
            routes=tuple(r.strip().upper() for r in _tuple(d.get("routes"))),
            timeout_s=float(d.get("timeout_s", 8.0)),
            retries=int(d.get("retries", 1)),
            surfaces=_tuple(d.get("surfaces")),
            reads=_tuple(d.get("reads")),
            emits=_tuple(d.get("emits")),
            guardrails=_tuple(d.get("guardrails")),
            hitl=bool(d.get("hitl", False)),
            degraded=str(d.get("degraded") or "").strip(),
            notes=str(d.get("notes") or "").strip(),
        )
    except (TypeError, ValueError) as exc:
        errors.append(f"agent '{name}' has a malformed field: {exc}")
        return None


def _parse(text: str) -> Manifest:
    try:
        import yaml
    except ImportError:                                  # pragma: no cover
        return Manifest(errors=("PyYAML is not installed — manifest unavailable",))

    agents: dict[str, AgentDef] = {}
    topology: dict[str, Any] = {}
    errors: list[str] = []

    for raw in _YAML_BLOCK.findall(text):
        try:
            doc = yaml.safe_load(raw)
        except Exception as exc:                         # noqa: BLE001 — parse boundary
            errors.append(f"unparseable yaml block: {exc}")
            continue
        if not isinstance(doc, dict):
            continue
        if "topology" in doc:
            topology = doc["topology"] or {}
            continue
        if "agent" not in doc:
            continue
        a = _build_agent(doc, errors)
        if not a:
            continue
        if a.agent in agents:
            errors.append(f"agent '{a.agent}' is declared twice")
            continue
        agents[a.agent] = a

    # Structural checks that only make sense once every block is loaded.
    nodes = set(topology.get("nodes") or [])
    seen_routes: dict[str, str] = {}
    for a in agents.values():
        if a.graph_node and nodes and a.graph_node not in nodes:
            errors.append(f"agent '{a.agent}' claims graph_node '{a.graph_node}' "
                          f"which is not in topology.nodes")
        if a.unrouted_fallback and nodes and a.unrouted_fallback not in nodes:
            errors.append(f"agent '{a.agent}' falls back to '{a.unrouted_fallback}' "
                          f"which is not in topology.nodes")
        if a.hosted_by and a.hosted_by not in agents:
            errors.append(f"agent '{a.agent}' is hosted_by unknown agent '{a.hosted_by}'")
        if a.kind == "worker" and not a.graph_node and not a.unrouted_fallback and a.routes:
            errors.append(f"agent '{a.agent}' has routes but neither graph_node nor "
                          f"unrouted_fallback — its routes would be dropped")
        for r in a.routes:
            if r in seen_routes:
                errors.append(f"route '{r}' is claimed by both '{seen_routes[r]}' and '{a.agent}'")
            seen_routes[r] = a.agent

    return Manifest(agents=agents, topology=topology, errors=tuple(errors))


@lru_cache(maxsize=1)
def load() -> Manifest:
    """Parse AGENTS.md once per process. Never raises."""
    try:
        text = MANIFEST_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("agents_manifest_unreadable", path=str(MANIFEST_PATH), error=str(exc))
        return Manifest(errors=(f"cannot read {MANIFEST_PATH}: {exc}",))
    m = _parse(text)
    if m.errors:
        logger.error("agents_manifest_invalid", errors=list(m.errors))
    return m


def reload() -> Manifest:
    """Drop the cache and re-read (tests, and editing AGENTS.md during dev)."""
    load.cache_clear()
    return load()


def status() -> dict:
    """Manifest health for /api/orchestrator/status."""
    m = load()
    return {
        "path": str(MANIFEST_PATH),
        "loaded": bool(m.agents),
        "agents": len(m.agents),
        "routes": len(m.route_map()),
        "errors": list(m.errors),
        "unreachable_agents": [
            {"agent": a.agent, "routes": list(a.routes), "folds_into": a.unrouted_fallback}
            for a in m.unreachable()
        ],
        "hitl_required": m.hitl_required(),
        "unresolved_routes": unresolved_routes(),
    }


if __name__ == "__main__":                               # python -m app.agents.manifest
    import json
    m = load()
    print(f"AGENTS.md — {len(m.agents)} agents, {len(m.route_map())} route labels\n")
    print(f"{'agent':16} {'kind':8} {'node':10} {'reach':6} routes")
    print("-" * 78)
    for a in sorted(m.agents.values(), key=lambda x: (x.kind, x.agent)):
        print(f"{a.agent:16} {a.kind:8} {str(a.dispatch_node or '-'):10} "
              f"{'yes' if a.reachable else 'NO':6} {', '.join(a.routes) or '-'}")
    if m.unreachable():
        print("\nGAPS — routed but not executed by any graph node:")
        for a in m.unreachable():
            print(f"  {a.agent:16} {', '.join(a.routes)} -> folds into '{a.unrouted_fallback}'")
    if m.hitl_required():
        print(f"\nHITL required: {', '.join(m.hitl_required())}")
    if m.errors:
        print("\nERRORS:")
        for e in m.errors:
            print(f"  - {e}")
        raise SystemExit(1)
    print("\nmanifest OK")
