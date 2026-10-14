"""Pin what runs (app/agents/agent_lock.py). The first test is the one that matters day to
day: it fails when an agent module or a system prompt was edited without re-locking."""
import json

import pytest

from app.agents import agent_lock as L


def test_what_runs_is_what_was_locked():
    st = L.status()
    assert st["locked"], "no agents.lock.json: run python scripts/lock_agents.py"
    assert st["changed"] == [], "changed since the lock; if intended, run python scripts/lock_agents.py and commit it"


def test_every_declared_agent_and_every_prompt_is_in_the_lock():
    from app.agents import manifest
    lock = L.read_lock()
    assert set(lock["modules"]) == set(manifest.load().agents)
    assert all(m["sha256"] for m in lock["modules"].values())
    assert {"select", "compose", "intent", "judge", "untrusted_data_policy"} <= set(lock["prompts"])


def test_one_changed_character_in_a_prompt_is_noticed(monkeypatch):
    from app.agents import query_agent
    monkeypatch.setattr(query_agent, "SELECT_SYSTEM", query_agent.SELECT_SYSTEM + " ")
    st = L.status()
    assert not st["ok"] and st["changed"] == ["prompt select changed"]
    assert st["prompt_version"] != st["locked_prompt_version"]


def test_a_changed_module_is_named(tmp_path, monkeypatch):
    lock = L.read_lock()
    lock["modules"]["query"]["sha256"] = "0" * 64
    f = tmp_path / "agents.lock.json"
    f.write_text(json.dumps(lock), encoding="utf-8")
    monkeypatch.setattr(L, "LOCK", f)
    assert L.status()["changed"] == ["agent query: app/agents/query_agent.py changed"]


def test_line_endings_do_not_count_as_a_change():
    assert L._sha("a\r\nb\r\n") == L._sha("a\nb\n")


def test_production_refuses_to_start_on_a_mismatch_and_development_does_not(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "LOCK", tmp_path / "missing.json")
    assert L.enforce(production=False)["ok"] is False
    with pytest.raises(RuntimeError):
        L.enforce(production=True)
