"""
Deterministic DEMO_MODE response cache.

This is not a second query engine. Scripted demo lines are still answered by the
existing heuristic selector + whitelisted ZCQL templates, then cached in memory so
repeated demo turns are byte-stable and fast. Unknown questions fall back to the
normal offline path in chat.py.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from app.agents.heuristics import heuristic_select
from app.agents.query_agent import query_agent_run


_WS = re.compile(r"\s+")
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d"), None)


def _normalize(text: str) -> str:
    return _WS.sub(" ", (text or "").translate(_ZERO_WIDTH).casefold()).strip()


@dataclass(frozen=True)
class DemoScript:
    key: str
    canonical_query: str
    aliases: tuple[str, ...]


_SCRIPTS: tuple[DemoScript, ...] = (
    DemoScript(
        key="wow1_kn_rajajinagar_chain_snatching",
        canonical_query="ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು",
        aliases=(
            "ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು",
            "rajajinagar chain snatching kannada demo",
        ),
    ),
    DemoScript(
        key="wow2_yellappa_cross_case",
        canonical_query="find suspect Yellappa",
        aliases=(
            "find suspect Yellappa",
            "who is Yellappa",
            "look up Yellappa",
        ),
    ),
    DemoScript(
        key="wow3_patrol_hotspots",
        canonical_query="where should I increase patrols this weekend",
        aliases=(
            "where should I increase patrols this weekend",
            "where are the theft hotspots",
            "show hotspots",
        ),
    ),
    DemoScript(
        key="rajajinagar_chain_snatching",
        canonical_query="show chain snatching in Rajajinagar",
        aliases=(
            "show chain snatching in Rajajinagar",
            "chain snatching in Rajajinagar",
        ),
    ),
    DemoScript(
        key="repeat_offenders",
        canonical_query="who are the repeat offenders",
        aliases=(
            "who are the repeat offenders",
            "show repeat offenders",
        ),
    ),
)

_SCRIPT_BY_ALIAS = {
    _normalize(alias): script
    for script in _SCRIPTS
    for alias in (script.canonical_query, *script.aliases)
}

def _load_question_bank():
    try:
        import sqlite3, os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(base_dir, "app", "intelligent.db")
        if not os.path.exists(db_path):
            db_path = os.path.join(base_dir, "intelligent.db")
        if not os.path.exists(db_path):
            return
        con = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, question_en, question_kn FROM question_bank").fetchall()
        con.close()
        for r in rows:
            q_en = r["question_en"]
            q_kn = r["question_kn"]
            s = DemoScript(key=f"bank_{r['id']}", canonical_query=q_en or q_kn, aliases=(q_en, q_kn))
            if q_en:
                _SCRIPT_BY_ALIAS[_normalize(q_en)] = s
            if q_kn:
                _SCRIPT_BY_ALIAS[_normalize(q_kn)] = s
    except Exception:
        pass

_load_question_bank()
_CACHE: dict[str, dict[str, Any]] = {}


def clear_demo_cache() -> None:
    """Test helper and operational escape hatch."""
    _CACHE.clear()


def cache_info() -> dict[str, int]:
    return {"scripts": len(_SCRIPTS), "entries": len(_CACHE)}


async def scripted_query_result(
    user_text: str,
    *,
    lang: str,
    session_id: str,
    history: list[dict] | None = None,
) -> dict[str, Any] | None:
    """Return a cached scripted result for known demo lines, otherwise None."""
    script = _SCRIPT_BY_ALIAS.get(_normalize(user_text))
    if script is None:
        return None

    cache_key = f"{script.key}:{lang}"
    if cache_key not in _CACHE:
        result = await query_agent_run(
            script.canonical_query,
            lang=lang,
            session_id=session_id,
            history=history,
            selector=heuristic_select,
            compose_llm=None,
        )
        result["demo_cache_key"] = cache_key
        _CACHE[cache_key] = deepcopy(result)
        cached = deepcopy(result)
        cached["demo_cache_hit"] = False
        return cached

    cached = deepcopy(_CACHE[cache_key])
    cached["demo_cache_hit"] = True
    return cached
