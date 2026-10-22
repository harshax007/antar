"""Gangs found on relationships plus shared phones / accounts, never split across members
who do not reach each other; and closeness to serious cases as an explained lead."""
import networkx as nx

from app.services import graph_cache as g


def _world():
    return {
        "suspects": [{"suspect_id": s, "full_name": s, "phone_hash": ph} for s, ph in
                     [("A", "p1"), ("B", "p1"), ("C", "p1"), ("D", ""), ("E", ""), ("F", "")]],
        "relationships": [{"suspect_a": "D", "suspect_b": "E", "rel_type": "associate"}],
        "financial_links": [{"suspect_id": "E", "counterparty": "ACC-9", "txn_count": 4},
                            {"suspect_id": "F", "counterparty": "ACC-9", "txn_count": 9}],
        "crimes": [{"crime_id": "K1", "crime_type": "MURDER"}, {"crime_id": "K2", "crime_type": "THEFT"}],
        "crime_suspects": [{"crime_id": "K1", "suspect_id": "D"}, {"crime_id": "K2", "suspect_id": "A"}],
    }


def test_shared_phone_and_account_link_people_with_no_recorded_relationship():
    links = {(a, b, why.split()[1]) for a, b, _, why in g._key_links(_world())}
    assert ("A", "B", "phone") in links and ("B", "C", "phone") in links      # a chain, not a clique
    assert ("A", "C", "phone") not in links
    assert ("E", "F", "account") in links


def test_a_community_is_always_connected():
    G = nx.Graph([("A", "B"), ("C", "D")])
    parts = g._connected_communities(G, [{"A", "B", "C", "D"}])                # one "community", two pieces
    assert sorted(map(sorted, parts)) == [["A", "B"], ["C", "D"]]


def test_close_to_serious_cases_is_a_lead_with_its_path():
    w = _world()
    G = nx.Graph(); G.add_nodes_from(s["suspect_id"] for s in w["suspects"])
    G.add_edge("D", "E", weight=1.0)
    for a, b, wt, why in g._key_links(w):
        G.add_edge(a, b, weight=wt)
    pct, hidden, seeds = g._serious_proximity(G, w, {n: n for n in G})
    assert seeds == 1                                              # only D is named in a serious crime
    ids = [h["id"] for h in hidden]
    assert "D" not in ids                                          # a seed is not its own lead
    assert ids[0] == "E" and hidden[0]["steps"] == 1 and hidden[0]["nearest_serious_crime"] == "MURDER"
    f = next(h for h in hidden if h["id"] == "F")                  # reached through the shared account:
    assert f["steps"] == 2 and f["via"] == ["E"] and f["nearest_serious"] == "D"   # D - E =(ACC-9)= F
    assert pct["E"] > pct["A"]                                     # the theft ring is further away
