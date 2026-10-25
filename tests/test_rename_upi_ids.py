"""scripts/rename_upi_ids.py: placeholder UPI ids get realistic names everywhere, reversibly."""
import importlib.util
import os
import sqlite3

_spec = importlib.util.spec_from_file_location(
    "rename_upi_ids", os.path.join(os.path.dirname(__file__), "..", "scripts", "rename_upi_ids.py"))
ren = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ren)


def _db(tmp_path):
    p = str(tmp_path / "m.db")
    c = sqlite3.connect(p)
    c.executescript("""
      CREATE TABLE FIRs (fir_id TEXT, UPI_ID TEXT);
      CREATE TABLE money_accounts (account_id TEXT PRIMARY KEY, kind TEXT, label TEXT, district TEXT, bank TEXT, suspect_id TEXT, source TEXT);
      CREATE TABLE money_transactions (txn_id TEXT, ts TEXT, from_account TEXT, to_account TEXT, amount_inr INT, channel TEXT, purpose TEXT, fir_id TEXT, source TEXT);
      INSERT INTO FIRs VALUES ('C1','user1050@bank'),('C2','user1050@bank'),('C3','user1226@bank'),('C4','real.person@ybl'),('C5','');
      INSERT INTO money_accounts VALUES ('user1050@bank','upi','user1050@bank','X','bank',NULL,'seeded'),
                                        ('user1226@bank','upi','user1226@bank','X','bank',NULL,'seeded'),
                                        ('cust.1@ybl','complainant','Complainant','X','ybl',NULL,'seeded');
      INSERT INTO money_transactions VALUES ('T1','t','cust.1@ybl','user1050@bank',100,'UPI','payment','C1','seeded'),
                                            ('T2','t','user1050@bank','user1226@bank',90,'UPI','layering','C1','seeded');
    """)
    c.commit(); c.close()
    return p


def test_rename_everywhere_then_revert(tmp_path):
    p, mp = _db(tmp_path), str(tmp_path / "map.csv")
    out = ren.rename(p, mp)
    assert out["renamed"] == 2 and out["FIRs.UPI_ID"] == 3
    c = sqlite3.connect(p)
    ids = [r[0] for r in c.execute("SELECT UPI_ID FROM FIRs ORDER BY fir_id")]
    assert not any(i.startswith("user") for i in ids) and ids[0] == ids[1] and ids[3] == "real.person@ybl"
    acc = dict(c.execute("SELECT account_id, label FROM money_accounts WHERE kind='upi'").fetchall())
    assert set(acc) == {ids[0], ids[2]} and all(" " in v for v in acc.values())     # "Ravi Gowda"
    t2 = c.execute("SELECT from_account, to_account FROM money_transactions WHERE txn_id='T2'").fetchone()
    assert t2 == (ids[0], ids[2])
    c.close()
    assert ren.rename(p, str(tmp_path / "again.csv"))["renamed"] == 0            # idempotent
    ren.revert(p, mp)
    c = sqlite3.connect(p)
    assert [r[0] for r in c.execute("SELECT UPI_ID FROM FIRs ORDER BY fir_id")][:3] == ["user1050@bank", "user1050@bank", "user1226@bank"]
    assert c.execute("SELECT to_account FROM money_transactions WHERE txn_id='T1'").fetchone()[0] == "user1050@bank"


def test_names_are_deterministic_and_unique():
    olds = [f"user{i}@bank" for i in range(1000, 1400)]
    a, b = ren.build_map(olds, set()), ren.build_map(olds, set())
    assert a == b and len({v[0] for v in a.values()}) == len(olds)
    assert all(ren.HANDLE_BANK[v[0].split("@")[1]] == v[2] for v in a.values())
