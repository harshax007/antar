"""Saved findings (app/services/saved_findings.py): kept per officer, in the database.

Each test uses its own empty database file.
"""
import pytest

from app.services import saved_findings as SF


@pytest.fixture(autouse=True)
def _own_database(tmp_path, monkeypatch):
    monkeypatch.setattr(SF, "DB_PATH", str(tmp_path / "saved.db"))
    monkeypatch.setattr(SF, "ensure_db_staged", lambda: None)
    monkeypatch.setattr(SF, "_ready", False)


def _finding(label="ACC-734551", bottom="Dossier on ACC-734551: 2 known, 2 derived, 0 inferred, 1 unknown."):
    return {"title": f"Research on {label}", "agent": "Research", "label": label,
            "result": {"status": "ok", "evidence_class": "d", "bottom_line": bottom,
                       "evidence": ["[K] Named as accused on 1 FIR (2021-06).", "[D] 1 district: Mandya."],
                       "limits": ["No hypothesis is proposed about an id with no profile."],
                       "method": ["Collect what is Known"], "next": ["run network ACC-734551"],
                       "anything_else": "must not be stored"}}


def test_a_finding_is_kept_whole_and_read_back_by_its_officer():
    got = SF.save("OF-1001", _finding())
    assert got["already"] is False and len(got["id"]) == 16
    listed = SF.list_for("OF-1001")
    assert listed["total"] == 1
    item = listed["items"][0]
    assert item["title"] == "Research on ACC-734551" and item["agent"] == "research"
    assert item["result"]["evidence_class"] == "D"
    assert item["result"]["evidence"] == ["[K] Named as accused on 1 FIR (2021-06).", "[D] 1 district: Mandya."]
    assert "anything_else" not in item["result"]          # only a finding's own fields are stored


def test_one_officer_never_sees_or_removes_anothers():
    mine = SF.save("OF-1001", _finding())
    assert SF.list_for("OF-2002") == {"items": [], "total": 0, "max": SF.MAX_PER_OFFICER}
    assert SF.remove("OF-2002", mine["id"]) is False
    assert SF.list_for("OF-1001")["total"] == 1
    assert SF.remove("OF-1001", mine["id"]) is True
    assert SF.list_for("OF-1001")["total"] == 0


def test_saving_the_same_finding_twice_keeps_one_copy():
    first = SF.save("OF-1001", _finding())
    again = SF.save("OF-1001", _finding())
    assert again["already"] is True and again["id"] == first["id"]
    assert SF.list_for("OF-1001")["total"] == 1
    # a changed answer about the same record is a new finding
    SF.save("OF-1001", _finding(bottom="Dossier on ACC-734551: 3 known, 2 derived, 0 inferred, 1 unknown."))
    assert SF.list_for("OF-1001")["total"] == 2


def test_the_newest_come_first_and_the_oldest_make_room(monkeypatch):
    monkeypatch.setattr(SF, "MAX_PER_OFFICER", 3)
    for i in range(5):
        SF.save("OF-1001", _finding(label=f"ACC-{i}", bottom=f"finding {i}"))
    labels = [x["label"] for x in SF.list_for("OF-1001")["items"]]
    assert labels == ["ACC-4", "ACC-3", "ACC-2"]


def test_an_empty_or_oversized_finding_is_refused():
    with pytest.raises(ValueError):
        SF.save("OF-1001", {"title": "", "result": {}})
    with pytest.raises(ValueError):
        SF.save("", _finding())
    # long text is cut to size, not rejected, and never exceeds the cap
    big = _finding(bottom="x" * 50_000)
    kept = SF.save("OF-1001", big)
    assert len(kept["result"]["bottom_line"]) == 1200
