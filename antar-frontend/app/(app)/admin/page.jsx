"use client";

import { useEffect, useState } from "react";
import RefStrip from "@/components/RefStrip";

const API = (process.env.NEXT_PUBLIC_API_URL || "");
const ROLES = ["Constable", "Inspector", "Analyst", "Admin"];

export default function Admin() {
  const [role, setRole] = useState("Admin");
  const [data, setData] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  function load(r) {
    setLoading(true); setData(null); setStatus(null);
    fetch(`${API}/api/audit?limit=60`, { headers: { "X-Role": r, "X-Officer": "OF-1004" } })
      .then((res) => { setStatus(res.status); return res.ok ? res.json() : null; })
      .then(setData)
      .catch(() => setStatus(0))
      .finally(() => setLoading(false));
  }
  useEffect(() => { load("Admin"); }, []);

  function pick(r) { setRole(r); load(r); }

  return (
    <div className="page">
      <div className="section-header">
        <h1>Admin · Audit Log</h1>
        <span className="sub">RBAC + every-call audit trail (M10)</span>
      </div>

      <RefStrip
        tag="K"
        title="Immutable audit ledger - every API call and AI answer is recorded"
        chips={[
          status === 200 ? { value: (data?.total ?? 0).toLocaleString(), label: "audited calls" } : null,
          { value: role, label: "viewing as" },
          status ? { value: status === 200 ? "authorized" : status === 403 ? "denied" : "waking up", label: "RBAC" } : null,
        ]}
        detailTitle="What gets audited"
        detail={<p style={{ margin: 0, fontSize: "12px", color: "#9fb3cc", lineHeight: 1.55 }}>
          Every /api call (officer, role, method, path, status) plus each AI answer's reasoning
          hash. Reads require the Admin role - the 403 you see as other roles is the enforcement
          working, not an error.
        </p>}
        style={{ marginBottom: 14 }}
      />

      <div className="panel" style={{ marginBottom: 14 }}>
        <h3>View as role</h3>
        <div className="suggested">
          {ROLES.map((r) => (
            <button key={r}
              style={{ borderColor: role === r ? "var(--primary)" : "", color: role === r ? "var(--text-primary)" : "" }}
              onClick={() => pick(r)}>{r}</button>
          ))}
        </div>
        <div style={{ marginTop: 12, fontSize: 13 }}>
          {loading ? <span style={{ color: "var(--text-secondary)" }}>Loading…</span>
            : status === 403 ? <span style={{ color: "var(--alert)" }}>403 - <b>{role}</b> is not authorized to read the audit log (Admin only). RBAC is enforced.</span>
            : status === 200 ? <span style={{ color: "var(--success)" }}> <b>{role}</b> authorized · {data?.total ?? 0} audited calls</span>
            : status === 0 ? <span style={{ color: "var(--alert)" }}>Could not reach the backend at {API}.</span>
            : null}
        </div>
      </div>

      {status === 200 && data?.rows && (
        <div className="panel">
          <h3>Recent API calls ({data.rows.length} shown)</h3>
          <table className="data-table">
            <thead><tr><th>Time (UTC)</th><th>Officer</th><th>Role</th><th>Method</th><th>Path</th><th>Status</th></tr></thead>
            <tbody>
              {data.rows.map((r, i) => (
                <tr key={i}>
                  <td>{(r.ts || "").slice(0, 19).replace("T", " ")}</td>
                  <td>{r.officer}</td>
                  <td>{r.role}</td>
                  <td>{r.method}</td>
                  <td style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }}>{r.path}</td>
                  <td><span className="badge" style={{
                    borderColor: r.status >= 400 ? "var(--alert)" : "var(--border)",
                    color: r.status >= 400 ? "var(--alert)" : "var(--text-secondary)",
                  }}>{r.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


