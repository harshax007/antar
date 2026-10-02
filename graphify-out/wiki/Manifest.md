# Manifest

> 24 nodes · cohesion 0.10

## Key Concepts

- **Manifest** (13 connections) — `app/agents/manifest.py`
- **AgentDef** (8 connections) — `app/agents/manifest.py`
- **.resolve()** (5 connections) — `app/agents/manifest.py`
- **.alias_map()** (3 connections) — `app/agents/manifest.py`
- **.dispatchable_nodes()** (3 connections) — `app/agents/manifest.py`
- **.fleet()** (3 connections) — `app/agents/manifest.py`
- **.graph_nodes()** (3 connections) — `app/agents/manifest.py`
- **.route_owner()** (3 connections) — `app/agents/manifest.py`
- **.unreachable()** (3 connections) — `app/agents/manifest.py`
- **.dispatch_node()** (2 connections) — `app/agents/manifest.py`
- **.reachable()** (2 connections) — `app/agents/manifest.py`
- **.route_map()** (2 connections) — `app/agents/manifest.py`
- **.hitl_required()** (1 connections) — `app/agents/manifest.py`
- **{ROUTE_LABEL: agent_id} — which agent a label is *addressed* to.** (1 connections) — `app/agents/manifest.py`
- **{alias: canonical_agent_id}, including each agent's own id.** (1 connections) — `app/agents/manifest.py`
- **Every node in the compiled graph, entry node included.** (1 connections) — `app/agents/manifest.py`
- **Nodes route_fn is allowed to RETURN — the compiled set minus the entry node.…** (1 connections) — `app/agents/manifest.py`
- **Agents the orchestrator registers (everything that does real work).** (1 connections) — `app/agents/manifest.py`
- **Workers with routes that no graph node executes — the honest gap list.** (1 connections) — `app/agents/manifest.py`
- **Look up by canonical id, alias, or route label. Case-insensitive.** (1 connections) — `app/agents/manifest.py`
- **One agent, exactly as declared in AGENTS.md.** (1 connections) — `app/agents/manifest.py`
- **The node a route addressed to this agent actually reaches. `graph_node` when…** (1 connections) — `app/agents/manifest.py`
- **True when a graph turn can actually execute this agent.** (1 connections) — `app/agents/manifest.py`
- **{ROUTE_LABEL: graph_node} — generated replacement for _ROUTE_MAP.** (1 connections) — `app/agents/manifest.py`

## Relationships

- [manifest.py](manifest.py.md) (6 shared connections)

## Source Files

- `app/agents/manifest.py`

## Audit Trail

- EXTRACTED: 34 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*