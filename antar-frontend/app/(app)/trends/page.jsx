"use client";

import { useEffect, useState } from "react";
import RefStrip from "@/components/RefStrip";

const API = (process.env.NEXT_PUBLIC_API_URL || "");
const cap = (s) => (s || "").replace(/_/g, " ");
const TYPES = ["", "theft", "robbery", "chain_snatching", "burglary", "assault", "vehicle_theft", "cheating_fraud"];

function Chart({ data }) {
  if (!data?.length) return <div className="loading-block">No data.</div>;
  const ns = data.map((d) => d.n);
  const max = Math.max(...ns, 1), min = Math.min(...ns, 0), rng = max - min || 1;
  const W = 600, H = 150, pad = 6;
  const x = (i) => (i / (data.length - 1 || 1)) * (W - 2 * pad) + pad;
  const y = (v) => H - pad - ((v - min) / rng) * (H - 2 * pad);
  const line = data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.n).toFixed(1)}`).join(" ");
  const area = `M${x(0)},${H - pad} ` + data.map((d, i) => `L${x(i).toFixed(1)},${y(d.n).toFixed(1)}`).join(" ") + ` L${x(data.length - 1)},${H - pad} Z`;
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 170, display: "block" }} preserveAspectRatio="none">
        <path d={area} fill="rgba(59,130,246,.12)" />
        <path d={line} fill="none" stroke="var(--primary)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-secondary)", fontSize: 10, marginTop: 4 }}>
        {data.map((d, i) => <span key={i} style={{ fontVariantNumeric: "tabular-nums" }}>{(d.month || "").slice(2)}</span>)}
      </div>
    </div>
  );
}

function Bars({ rows }) {
  if (!rows?.length) return <div className="loading-block">No data.</div>;
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

function Chips({ options, value, onChange, labelAll = "All" }) {
  return (
    <div className="suggested" style={{ marginBottom: 12 }}>
      {options.map((o) => (
        <button key={o || "all"}
          style={{ borderColor: value === o ? "var(--primary)" : "", color: value === o ? "var(--text-primary)" : "" }}
          onClick={() => onChange(o)}>
          {o ? cap(o) : labelAll}
        </button>
      ))}
    </div>
  );
}

export default function Trends() {
  const [ctype, setCtype] = useState("");
  const [trend, setTrend] = useState(null);
  const [by, setBy] = useState("type");
  const [bd, setBd] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    const q = ctype ? `?crime_type=${ctype}&months=12` : `?months=12`;
    fetch(`${API}/api/analytics/trends${q}`).then((r) => r.json()).then((d) => setTrend(d.series || [])).catch(() => setErr(true));
  }, [ctype]);

  useEffect(() => {
    fetch(`${API}/api/analytics/breakdown?by=${by}`).then((r) => r.json()).then((d) => setBd(d.rows || [])).catch(() => {});
  }, [by]);

  if (err) return (
    <div className="page"><div className="loading-block">
      Could not reach the backend at {API}.<br />Run: <code>uvicorn main:app --port 8000</code>
    </div></div>
  );

  return (
    <div className="page">
      <div className="section-header">
        <h1>Trend &amp; Pattern Analytics</h1>
        <span className="sub">crime over time · by type / zone / status</span>
      </div>

      <RefStrip
        tag="K"
        title={`Monthly registrations${ctype ? ` - ${cap(ctype)}` : " - all crime types"}, computed from official FIR records`}
        chips={[
          trend ? { value: trend.length, label: "months" } : null,
          trend ? { value: trend.reduce((s, d) => s + (d.n || 0), 0).toLocaleString(), label: "records" } : null,
          bd ? { value: bd.length, label: `by ${by}` } : null,
        ]}
        detailTitle="How these figures are derived"
        detail={<p style={{ margin: 0, fontSize: "12px", color: "#9fb3cc", lineHeight: 1.55 }}>
          Counts are aggregated per calendar month directly from the FIR table via whitelisted
          ZCQL templates (T3 trend / T13 breakdown) - no model output, no interpolation.
        </p>}
        style={{ marginBottom: 14 }}
      />

      <div className="panel">
        <h3>Monthly trend · {ctype ? cap(ctype) : "all crimes"}</h3>
        <Chips options={TYPES} value={ctype} onChange={setCtype} labelAll="All crime" />
        {trend ? <Chart data={trend} /> : <div className="loading-block">Loading…</div>}
      </div>

      <div className="panel" style={{ marginTop: 14 }}>
        <h3>Breakdown</h3>
        <Chips options={["type", "zone", "status"]} value={by} onChange={setBy} />
        {bd ? <Bars rows={bd} /> : <div className="loading-block">Loading…</div>}
      </div>
    </div>
  );
}


