"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import RefStrip from "@/components/RefStrip";

const API = (process.env.NEXT_PUBLIC_API_URL || "");
const FACTORS = ["recency", "frequency", "severity", "centrality"];

function riskColor(r) {
  return r >= 60 ? "var(--alert)" : r >= 35 ? "var(--accent-brain)" : "var(--text-primary)";
}

function RiskBars({ factors, attributions }) {
  return (
    <div className="bars">
      {FACTORS.map((k) => {
        const val = factors[k] || 0;
        const attrib = attributions?.[k] || 0;
        return (
          <div className="bar-row" key={k} style={{ gridTemplateColumns: "100px 1fr 40px 65px" }}>
            <span className="cap">{k}</span>
            <span className="track"><span className="fill" style={{ width: `${val * 100}%` }} /></span>
            <span className="n">{val.toFixed(2)}</span>
            <span className="contrib" style={{ color: "var(--primary)", fontSize: "11px", textAlign: "right" }}>
              +{attrib.toFixed(1)} pts
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function Profiles() {
  const [reg, setReg] = useState(null);
  const [sel, setSel] = useState(null);
  const [prof, setProf] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/profile/registry?min_priors=5&limit=30`)
      .then((r) => r.json())
      .then((d) => {
        setReg(d.offenders || []);
        if (d.offenders?.length) select(d.offenders[0].suspect_id);
      })
      .catch(() => setErr(true));
  }, []);

  async function select(id) {
    setSel(id);
    setProf(null);
    try {
      setProf(await (await fetch(`${API}/api/profile/${id}`)).json());
    } catch {
      setProf({ error: true });
    }
  }

  if (err) return (
    <div className="page"><div className="loading-block">
      Could not reach the backend at {API}.<br />Run: <code>uvicorn main:app --port 8000</code>
    </div></div>
  );
  if (!reg) return <div className="page"><div className="loading-block">Loading registry…</div></div>;

  return (
    <div className="page">
      <div className="section-header">
        <h1>Repeat-Offender Registry</h1>
        <span className="sub">habitual offenders · transparent 4-factor risk scoring</span>
      </div>

      <RefStrip
        tag="K"
        title="Registry compiled from chargesheeted priors in official records"
        chips={[
          { value: reg.length, label: "offenders" },
          { value: "4", label: "risk factors" },
          prof && !prof.error ? { value: prof.risk_score, label: "selected risk" } : null,
        ]}
        detailTitle="How the risk score works"
        detail={<p style={{ margin: 0, fontSize: "12px", color: "#9fb3cc", lineHeight: 1.55 }}>
          Score = weighted recency, frequency, severity and network-centrality - each factor's
          point contribution is shown on the profile, and every profile passes the Safe-AI bias
          check before display. No demographic feature enters the score.
        </p>}
        style={{ marginBottom: 14 }}
      />

      <div className="grid cols-2">
        <div className="panel">
          <h3>Offenders ({reg.length})</h3>
          <table className="data-table">
            <thead><tr><th>Name</th><th>Priors</th><th>Zone</th><th>Risk</th></tr></thead>
            <tbody>
              {reg.map((o) => (
                <tr key={o.suspect_id} onClick={() => select(o.suspect_id)}
                    style={{ cursor: "pointer", background: sel === o.suspect_id ? "var(--bg-elevated)" : "" }}>
                  <td>{o.full_name}{o.alias ? <span style={{ color: "var(--text-secondary)" }}> · {o.alias}</span> : ""}</td>
                  <td>{o.prior_count}</td>
                  <td>{o.zone}</td>
                  <td><b style={{ color: riskColor(o.risk_score) }}>{o.risk_score}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          {!prof && <div className="loading-block">Select an offender…</div>}
          {prof?.error && <div className="loading-block">Could not load that profile.</div>}
          {prof && !prof.error && (
            <>
              <h3>{prof.full_name}{prof.alias ? ` - alias ${prof.alias}` : ""}</h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                <Link href={`/network?suspect_id=${sel}`} className="cite"
                      style={{ textDecoration: "none", cursor: "pointer", display: "inline-block" }}>
                  View in Network explorer
                </Link>
                {prof.anti_bias_cleared === true && (
                  <span className="badge" style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", borderColor: "#10b981" }}>
                     Safe AI: Bias Cleared
                  </span>
                )}
                {prof.anti_bias_cleared === false && (
                  <span className="badge" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", borderColor: "#ef4444" }}>
                    Safe AI: Flagged
                  </span>
                )}
              </div>
              
              {prof.bias_warnings?.length > 0 && (
                <div style={{ padding: "8px 12px", background: "rgba(239,68,68,0.05)", borderLeft: "3px solid #ef4444", fontSize: 13, marginBottom: 16 }}>
                  <b>Bias Warnings:</b>
                  <ul style={{ margin: "4px 0 0 16px" }}>
                    {prof.bias_warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}

              <div className="kpi-tile" style={{ padding: 0, marginBottom: 16 }}>
                <div className="label">Risk score</div>
                <div className="value" style={{ color: riskColor(prof.risk_score) }}>
                  {prof.risk_score}<span style={{ fontSize: 14, color: "var(--text-secondary)" }}> / 100</span>
                </div>
              </div>

              <h3>Risk factors</h3>
              <RiskBars factors={prof.factors || {}} attributions={prof.risk_attributions || {}} />

              <h3 style={{ marginTop: 18 }}>Modus operandi</h3>
              <div style={{ fontSize: 13.5 }}>{prof.mo_summary}</div>

              {prof.leads?.length > 0 && (
                <>
                  <h3 style={{ marginTop: 18 }}>Suggested leads</h3>
                  <ul style={{ fontSize: 13.5, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
                    {prof.leads.map((l, i) => <li key={i}>{l}</li>)}
                  </ul>
                </>
              )}

              {prof.similar_cases?.length > 0 && (
                <>
                  <h3 style={{ marginTop: 18 }}>Similar past cases · Second Brain</h3>
                  {prof.similar_cases.map((s, i) => (
                    <div className="alert-card" key={i}
                         style={{ borderLeftColor: "var(--accent-brain)", background: "rgba(245,158,11,.07)" }}>
                      <div style={{ fontSize: 12.5 }}>{(s.summary || "").slice(0, 160)}…</div>
                    </div>
                  ))}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}


