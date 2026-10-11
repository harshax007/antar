"""Brain console - one agent on one record, in Antar's template, or an honest refusal."""
import pytest

from app.agents import brain_console as C
from app.agents import manifest
from app.core import antar_identity as identity

FIR_NO_ACCUSED = {"accused": "", "fir_i": "951248", "station": "Bellanduru PS",
                  "district": "Bengaluru City", "crime_group": "THEFT"}
NEEDS_SUSPECT = ["network", "profile", "research", "advocate", "recall"]


@pytest.fixture(autouse=True)
def _fresh_cache():
    C._cache.clear()
    yield
    C._cache.clear()


def test_every_card_is_an_agent_the_manifest_declares():
    declared = manifest.load().agents
    for key, card in C.AGENTS.items():
        assert card.manifest in declared, f"{key} points at '{card.manifest}', which AGENTS.md does not declare"
        assert card.method and card.refuses and card.purpose


def test_identity_pack_is_built_from_the_constitution():
    p = C.identity_pack()
    assert p["name"] == identity.NAME
    assert [l["law"] for l in p["laws"]] == [n for n, _ in identity.LAWS]
    assert [s["step"] for s in p["thinking"]] == [n for n, _ in identity.THINKING]
    assert {a["id"] for a in p["agents"]} == set(C.AGENTS)
    assert all(a["role"] for a in p["agents"])            # read from the manifest, never blank
    assert {"help", "agents", "clear"} <= {c["cmd"] for c in p["commands"]}


def test_the_prompt_carries_how_antar_thinks():
    prompt = identity.system_prompt("answer")
    for name, _ in identity.THINKING:
        assert name.upper() in prompt


@pytest.mark.parametrize("agent", NEEDS_SUSPECT)
def test_suspect_agents_refuse_a_record_with_no_accused(agent):
    r = C.run(agent, FIR_NO_ACCUSED)
    assert r["status"] == "refused" and r["evidence_class"] is None
    assert "no accused" in r["bottom_line"] and not r["evidence"]


@pytest.mark.parametrize("agent", NEEDS_SUSPECT)
def test_suspect_agents_refuse_an_id_that_is_not_in_the_registry(agent):
    r = C.run(agent, "S9999999")
    assert r["status"] == "refused" and "not in the suspect registry" in r["bottom_line"]


def test_place_agents_refuse_a_person():
    for agent in ("forecast", "geo", "pattern"):
        assert C.run(agent, "S0001")["status"] == "refused"


def test_unknown_agent_is_refused_with_the_nearest_name():
    r = C.run("netwrk", "S0001")
    assert r["status"] == "refused" and "network" in r["bottom_line"]


def test_typed_targets_are_classified_by_shape_only():
    assert C.parse_target("s0041").accused == "S0041"
    assert C.parse_target("ACC-414044").accused == "ACC-414044"
    assert C.parse_target("ev-12").fir_ref == "EV-12"
    assert C.parse_target("Bellanduru PS").station == "Bellanduru PS"
    assert C.parse_target("ACC-KA-500777").accused == "ACC-KA-500777"
    assert C.parse_target("upi:name@bank").upi == "name@bank"
    node = C.parse_target({**FIR_NO_ACCUSED, "vehicle": "KA-01-AB-1234"})
    assert node.vehicle == "KA-01-AB-1234" and node.fir_ref == ""
    # A node's number is its place in a list, not an id: it is not read as one.
    assert C.parse_target({"fir_i": "967"}).key() == C.Target().key()


def test_a_graph_record_is_matched_by_its_keys_never_by_a_row_number(monkeypatch):
    """The graph numbers nodes by list position, the registry numbers rows its own way, and
    the evidence ledger's 'EV-{i}' is a third numbering. Reading one as another answers
    about an unrelated case, so a dropped record is never looked up by number."""
    from app.services import evidence_ledger
    asked = []
    monkeypatch.setattr(evidence_ledger, "linkage", lambda ref, limit=8: asked.append(ref))
    r = C.run("linkage", {"accused": "", "fir_i": "967", "station": "Bagalkot Traffic PS"})
    assert not asked
    assert r["status"] == "empty" and "nothing to link it on" in r["bottom_line"]


def test_brain_linkage_counts_exact_keys_in_the_dataset_the_graph_draws():
    import os
    import sqlite3
    from app.agents.linkage_agent import brain_linkage
    from app.core.db_path import DB_PATH
    intel = os.path.normpath(os.path.join(os.path.dirname(C.__file__), "..", "..", "intelligent.db"))
    con = sqlite3.connect(f"file:{intel if os.path.exists(intel) else DB_PATH}?mode=ro", uri=True)
    acc, n = con.execute("SELECT Accused_ID, COUNT(*) FROM FIRs WHERE Accused_ID IS NOT NULL AND Accused_ID != '' "
                         "GROUP BY Accused_ID HAVING COUNT(*) BETWEEN 2 AND 40 LIMIT 1").fetchone()
    con.close()
    res = brain_linkage({"Accused_ID": acc})
    assert res["total"] == n and res["by_key"]["accused"] == {"value": acc, "firs": n}
    assert all(r["shares"] == [f"accused {acc}"] for r in res["rows"])
    assert brain_linkage({})["total"] == 0
    r = C.run("linkage", acc)
    assert r["status"] == "ok" and r["evidence_class"] == "K" and f"{n} FIRs" in r["bottom_line"].replace(",", "")


def test_a_result_is_in_the_template_and_cached_on_repeat():
    first = C.run("profile", "S0001")
    assert first["status"] == "ok" and first["evidence_class"] in identity.CLASSES
    assert first["bottom_line"] and first["method"] == list(C.AGENTS["profile"].method)
    assert any("not a forecast of what this person will do" in l for l in first["limits"])
    assert C.run("profile", "S0001")["cached"] is True


def test_a_crashing_agent_degrades_and_is_not_cached(monkeypatch):
    def boom(_t):
        raise RuntimeError("down")
    monkeypatch.setitem(C.AGENTS, "recall", C.Card("brain", "Recall", "suspect", "p", ("m",), "r", boom))
    r = C.run("recall", "S0001")
    assert r["status"] == "error" and not r["evidence"]
    assert ("recall", C.parse_target("S0001").key()) not in C._cache


def test_console_api_is_inspector_gated():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    assert c.get("/api/console/identity", headers={"X-Role": "Constable"}).status_code == 403
    ok = c.get("/api/console/identity", headers={"X-Role": "Inspector"})
    assert ok.status_code == 200 and ok.json()["name"] == identity.NAME
    r = c.post("/api/console/run", json={"agent": "network", "target": FIR_NO_ACCUSED},
               headers={"X-Role": "Inspector"})
    assert r.status_code == 200 and r.json()["status"] == "refused"


def test_the_evolution_record_counts_or_says_it_cannot(monkeypatch):
    """Every line is a count from a store, and a store that fails is reported, not zeroed."""
    rec = C.evolution()
    assert rec["version"] == identity.VERSION
    assert [r["what"] for r in rec["record"]][0] == "Identity"
    assert all(r["value"] and r["how"] for r in rec["record"])

    from app.services import audit_store
    monkeypatch.setattr(audit_store, "verify_chain_report", lambda: 1 / 0)
    broken = {r["what"]: r for r in C.evolution()["record"]}
    assert broken["Accountable"]["value"] == "not available"
    assert broken["Identity"]["value"] != "not available", "one unreadable store hid the others"


def test_identity_and_evolution_are_claimed_as_usps():
    claims = [c for c, _ in identity.USPS]
    assert "One identity on every answer" in claims and "Its growth is on the record" in claims
    assert any(c["cmd"] == "evolution" for c in C.COMMANDS), "the claim has no command to check it with"
