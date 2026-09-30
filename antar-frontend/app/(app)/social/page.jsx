"use client";

import { useEffect, useState } from "react";
import RefStrip from "@/components/RefStrip";

const API = (process.env.NEXT_PUBLIC_API_URL || "");
const cap = (s) => (s || "").replace(/_/g, " ");

function Bars({ rows }) {
  if (!rows?.length) return <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>No data.</div>;
  const max = Math.max(...rows.map((r) => r.n), 1);
  return (
    <div className="bars">
      {rows.map((r, i) => (
        <div className="bar-row" key={i}>
          <span className="cap" title={r.label}>{cap(r.label)}</span>
          <span className="track"><span className="fill" style={{ width: `${(r.n / max) * 100}%` }} /></span>
          <span className="n">{(r.n ?? 0).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export default function Social() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/social/demographics`).then((r) => r.json()).then(setD).catch(() => setErr(true));
  }, []);

  if (err) return (
    <div className="page"><div className="loading-block">
      Could not reach the backend at {API}.<br />Run: <code>uvicorn main:app --port 8000</code>
    </div></div>
  );
  if (!d) return <div className="page"><div className="loading-block">Loading…</div></div>;

  return (
    <div className="page">
      <div className="section-header">
        <h1>Socio-economic Insights</h1>
        <span className="sub">demographic correlations · for planning, not profiling</span>
      </div>

      <RefStrip
        tag="K"
        title="Demographic aggregates from official records - decision support for planning, never individual profiling"
        chips={[
          { value: (d.victims?.gender || []).reduce((s, r) => s + (r.n || 0), 0).toLocaleString(), label: "victim records" },
          { value: (d.offenders?.gender || []).reduce((s, r) => s + (r.n || 0), 0).toLocaleString(), label: "offender records" },
          { value: (d.crime_occupation || []).length, label: "crime types" },
        ]}
        detailTitle="Framing & limits"
        detail={<p style={{ margin: 0, fontSize: "12px", color: "#9fb3cc", lineHeight: 1.55 }}>{d.framing}</p>}
        style={{ marginBottom: 14 }}
      />

      <div className="grid cols-2">
        <div className="panel">
          <h3>Victims · gender</h3><Bars rows={d.victims.gender} />
          <h3 style={{ marginTop: 16 }}>Victims · age band</h3><Bars rows={d.victims.age_band} />
          <h3 style={{ marginTop: 16 }}>Victims · occupation</h3><Bars rows={d.victims.occupation} />
        </div>
        <div className="panel">
          <h3>Offenders · gender</h3><Bars rows={d.offenders.gender} />
          <h3 style={{ marginTop: 16 }}>Offenders · occupation</h3><Bars rows={d.offenders.occupation} />
        </div>
      </div>

      <div className="panel" style={{ marginTop: 14 }}>
        <h3>Crime type × offender occupation</h3>
        <table className="data-table">
          <thead><tr><th>Crime type</th><th>Most associated offender occupations</th></tr></thead>
          <tbody>
            {d.crime_occupation.map((c, i) => (
              <tr key={i}>
                <td style={{ textTransform: "capitalize" }}>{cap(c.crime_type)}</td>
                <td>
                  {c.top_occupations.map((o, j) => (
                    <span className="cite" key={j} style={{ marginRight: 6 }}>{cap(o.label)} <b>{o.n}</b></span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ color: "var(--text-secondary)", fontSize: 11.5, marginTop: 8 }}>
          Correlation, not causation - see the note above.
        </div>
      </div>
    </div>
  );
}


