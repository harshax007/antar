"""Case leads (app/services/case_leads.py): counted, each with what would settle it, and a
near-repeat lead only when the record itself shows one."""
import random
import sqlite3

import pytest

from app.services import case_leads as CL


@pytest.fixture(autouse=True)
def fresh():
    CL._cache.clear()
    yield
    CL._cache.clear()


def _conn(rows):
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE FIRs (fir_id, CrimeNo, District_Name, station, date, CrimeHead_Name, CrimeGroup_Name, FIR_Stage, "
              "Vehicle_Reg_No, UPI_ID, IP_Address, is_synthetic_row, has_synthetic_link, Latitude, Longitude, Beat_Name)")
    for r in rows:
        base = {"fir_id": "C1", "CrimeNo": None, "District_Name": "Mysuru City", "station": "PS-1", "date": "2023-01-01",
                "CrimeHead_Name": "Theft", "CrimeGroup_Name": "THEFT", "FIR_Stage": "Under Investigation", "Vehicle_Reg_No": None,
                "UPI_ID": None, "IP_Address": None, "is_synthetic_row": 0, "has_synthetic_link": 0, "Latitude": None,
                "Longitude": None, "Beat_Name": "B1"}
        base.update(r)
        c.execute(f"INSERT INTO FIRs ({', '.join(base)}) VALUES ({', '.join('?' * len(base))})", list(base.values()))
    return c


class TestSharedKeys:
    def test_a_key_on_two_firs_is_a_specific_lead_and_names_the_key(self):
        c = _conn([{"fir_id": "A", "Vehicle_Reg_No": "KA-09-M-1111"},
                   {"fir_id": "B", "Vehicle_Reg_No": "KA-09-M-1111", "District_Name": "Mandya"},
                   {"fir_id": "C", "Vehicle_Reg_No": "KA-01-X-0001"}])
        got = CL.shared_keys(c, "Mysuru City")
        assert got["total"] == 1 and got["specific"] == 1
        lead = got["leads"][0]
        assert lead["key"] == "KA-09-M-1111" and lead["key_type"] == "vehicle" and lead["firs"] == 2
        assert lead["districts"] == ["Mandya", "Mysuru City"] and "seizure memo" in lead["would_settle"]

    def test_a_key_on_many_firs_is_marked_weak_and_listed_last(self):
        rows = [{"fir_id": f"W{i}", "UPI_ID": "common@bank"} for i in range(9)]
        rows += [{"fir_id": "S1", "IP_Address": "10.0.0.7"}, {"fir_id": "S2", "IP_Address": "10.0.0.7"}]
        leads = CL.shared_keys(_conn(rows), "Mysuru City")["leads"]
        assert [l["specific"] for l in leads] == [True, False] and leads[1]["firs"] == 9

    def test_a_key_that_never_touches_this_district_is_not_its_lead(self):
        c = _conn([{"fir_id": "A", "Vehicle_Reg_No": "KA-1", "District_Name": "Mandya"},
                   {"fir_id": "B", "Vehicle_Reg_No": "KA-1", "District_Name": "Hassan"}])
        assert CL.shared_keys(c, "Mysuru City") == {**CL.shared_keys(c, "Mysuru City"), "total": 0, "leads": []}

    def test_seeded_rows_are_said_to_be_seeded(self):
        c = _conn([{"fir_id": "A", "Vehicle_Reg_No": "KA-1", "has_synthetic_link": 1}, {"fir_id": "B", "Vehicle_Reg_No": "KA-1"}])
        assert CL.shared_keys(c, "Mysuru City")["leads"][0]["seeded"] is True


class TestKnox:
    def _clustered(self, rng):
        """Bursts: a burglary, then two more nearby within a week."""
        pts = []
        for k in range(80):
            la, lo, d = 12.0 + rng.random() * 0.5, 76.0 + rng.random() * 0.5, rng.randrange(0, 1500)
            pts += [(la, lo, d), (la + 0.001, lo + 0.001, d + 3), (la - 0.001, lo + 0.001, d + 6)]
        return pts

    def test_real_clustering_is_found(self):
        k = CL.knox(self._clustered(random.Random(1)))
        assert k["ratio"] > 3 and k["p"] < 0.05 and k["observed"] >= 200

    def test_places_and_dates_that_are_unrelated_show_nothing(self):
        rng = random.Random(2)
        spots = [(12.0 + rng.random() * 0.05, 76.0 + rng.random() * 0.05) for _ in range(40)]
        pts = [(*rng.choice(spots), rng.randrange(0, 1500)) for _ in range(400)]
        pts = [(la + i * 1e-6, lo, d) for i, (la, lo, d) in enumerate(pts)]          # no two at the same point
        k = CL.knox(pts)
        assert k["p"] > 0.05 and 0.6 < k["ratio"] < 1.6

    def test_several_firs_at_one_point_on_one_day_are_not_a_near_repeat(self):
        """The register's duplicates: counted apart, never as 'another burglary nearby'."""
        rng = random.Random(3)
        pts = []
        for _ in range(120):
            la, lo, d = 12.0 + rng.random() * 0.5, 76.0 + rng.random() * 0.5, rng.randrange(0, 1500)
            pts += [(la, lo, d)] * 3
        k = CL.knox(pts)
        assert k["same_point_same_day"] == 360 and k["observed"] < 10

    def test_it_is_repeatable(self):
        pts = self._clustered(random.Random(4))
        assert CL.knox(pts) == CL.knox(pts)


class TestNearRepeatLead:
    def _burglaries(self, n, clustered):
        rng = random.Random(9)
        rows = []
        for k in range(n // 3):
            la, lo = 12.0 + rng.random() * 0.4, 76.0 + rng.random() * 0.4
            d0 = rng.randrange(0, 700)
            for j in range(3):
                dd = d0 + (j * 4 if clustered else rng.randrange(0, 700))
                la2, lo2 = (la + j * 0.001, lo) if clustered else (12.0 + rng.random() * 0.4, 76.0 + rng.random() * 0.4)
                import datetime
                rows.append({"fir_id": f"B{k}-{j}", "CrimeGroup_Name": "BURGLARY - NIGHT", "Latitude": la2, "Longitude": lo2,
                             "date": (datetime.date(2022, 1, 1) + datetime.timedelta(days=dd % 700)).isoformat()})
        return rows

    def test_too_few_located_burglaries_is_said_not_tested(self):
        nr = CL.near_repeat(_conn(self._burglaries(30, True)), "Mysuru City")
        assert nr["tested"] is False and nr["supported"] is False and "Too few" in nr["text"]

    def test_the_lead_is_offered_only_when_the_record_shows_it(self):
        yes = CL.near_repeat(_conn(self._burglaries(300, True)), "Mysuru City")
        assert yes["supported"] is True and "times as common as chance" in yes["text"]
        CL._cache.clear()
        no = CL.near_repeat(_conn(self._burglaries(300, False)), "Mysuru City")
        assert no["supported"] is False and "does not show" in no["text"]

    def test_seeded_rows_are_left_out_of_the_measurement(self):
        rows = [{**r, "is_synthetic_row": 1} for r in self._burglaries(300, True)]
        assert CL.near_repeat(_conn(rows), "Mysuru City")["located_firs"] == 0


def test_the_whole_page_of_leads_calls_no_model(monkeypatch):
    from app.services import quickml

    async def boom(*a, **k):
        raise AssertionError("case leads called a language model")
    monkeypatch.setattr(quickml, "quickml_generate", boom)
    monkeypatch.setattr(CL, "cross_border", lambda zone, limit=6: {"total": 0, "links": []})
    out = CL.build(_conn([{"fir_id": "A", "Vehicle_Reg_No": "KA-1"}, {"fir_id": "B", "Vehicle_Reg_No": "KA-1"}]), "Mysuru City")
    assert out["shared_keys"]["total"] == 1 and out["near_repeat"]["tested"] is False and out["evidence_class"] == "D"
    assert CL.build(None, "  ")["near_repeat"] is None
