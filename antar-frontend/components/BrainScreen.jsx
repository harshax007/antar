"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import NetworkGraph from "@/components/NetworkGraph";
import { useLang } from "@/components/Providers";
import AntarBrainNav from "@/components/AntarBrainNav";

const API = (process.env.NEXT_PUBLIC_API_URL || "");
const SEED_SUSPECT = "S0001"; // Raju K. / alias Yellappa - the demo's WOW-2 cross-case anchor.
const fmt = (n) => (n ?? 0).toLocaleString();
const cap = (s) => (s || "").replace(/_/g, " ");
const shortLabel = (s, n = 10) => (s || "").length > n ? s.slice(0, n - 1) + "…" : s;

export default function BrainScreen() {
  const router = useRouter();
  const { lang } = useLang();
  const kn = lang === "kn";

  const [overview, setOverview] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [related, setRelated] = useState(null);
  const [linkage, setLinkage] = useState(null);
  const [registry, setRegistry] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [activity, setActivity] = useState([]);
  const [graph, setGraph] = useState(null);
  const [depth, setDepth] = useState(2);
  const [err, setErr] = useState(false);
  const [activeTile, setActiveTile] = useState(null);
  const [live, setLive] = useState([]);
  const drillRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/api/dashboard/overview`).then((r) => r.json()).then(setOverview).catch(() => setErr(true));
    fetch(`${API}/api/alerts`).then((r) => r.json()).then((d) => setAlerts(d.alerts || [])).catch(() => {});
    fetch(`${API}/api/brain/related?suspect_ids=${SEED_SUSPECT}`).then((r) => r.json()).then(setRelated).catch(() => {});
    fetch(`${API}/api/linkage/FIR-2026-0891`).then((r) => r.json()).then((d) => setLinkage(d.linkage || null)).catch(() => {});
    fetch(`${API}/api/profile/registry`).then((r) => r.json()).then((d) => setRegistry(d.offenders || [])).catch(() => {});
    fetch(`${API}/api/pattern`).then((r) => r.json()).then((d) => setPatterns(d.clusters || [])).catch(() => {});
    fetch(`${API}/api/brain/activity`).then((r) => r.json()).then((d) => setActivity(d.activity || [])).catch(() => {});
  }, []);

  useEffect(() => {
    fetch(`${API}/api/graph/${SEED_SUSPECT}?depth=${depth}`).then((r) => r.json()).then(setGraph).catch(() => setGraph(null));
  }, [depth]);

  useEffect(() => {
    const wsUrl = API.replace("http://", "ws://").replace("https://", "wss://") + "/api/stream/events";
    let ws, reconnectTimer;
    function connect() {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "emergency_dispatch" || msg.type === "reasoning_trace") {
            setLive((prev) => [{ ...msg, _ts: Date.now() }, ...prev].slice(0, 8));
          }
        } catch {}
      };
      ws.onclose = () => { reconnectTimer = setTimeout(connect, 3000); };
      ws.onerror = () => ws.close();
    }
    connect();
    return () => { if (ws) ws.close(); clearTimeout(reconnectTimer); };
  }, []);

  const k = overview?.kpis;
  const topRisk = registry[0];
  const featuredLink = related?.results?.[0]?.links?.[0];
  const seedName = graph?.nodes?.find((n) => n.type === "seed")?.label || "Raju K.";

  const tiles = useMemo(() => {
    if (!k) return [];
    return [
      { key: "fir", label: kn ? "ಒಟ್ಟು FIR" : "Total FIRs", value: fmt(k.total_crimes), cls: "" },
      { key: "open", label: kn ? "ಬಾಕಿ ಪ್ರಕರಣಗಳು" : "Open Cases", value: fmt(k.open_cases), cls: "" },
      { key: "alerts", label: kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು" : "Active Alerts", value: fmt(alerts.length), cls: "red" },
      { key: "risk", label: kn ? "ಅಗ್ರ ಅಪಾಯ ಸ್ಕೋರ್" : "Top Risk Score", value: topRisk ? `${topRisk.risk_score}%` : "—", cls: "cyan" },
      { key: "links", label: kn ? "ಅಡ್ಡ-ಪ್ರಕರಣ ಕೊಂಡಿಗಳು" : "Cross-case Links", value: fmt(related?.results?.[0]?.links?.length || 0), cls: "amber" },
      { key: "patterns", label: kn ? "ಪಟ್ಟಿ ಮಾದರಿಗಳು" : "Patterns Indexed", value: fmt(patterns.length), cls: "" },
    ];
  }, [k, alerts, topRisk, related, patterns, kn]);

  function buildDrill(key) {
    if (!k) return null;
    switch (key) {
      case "fir": {
        const trend = overview.trend_12m || [];
        return {
          title: kn ? "ಒಟ್ಟು FIR" : "Total FIRs", value: fmt(k.total_crimes),
          substats: [
            [kn ? "ಬಾಕಿ" : "Open", fmt(k.open_cases)],
            [kn ? "ಚಾರ್ಜ್‌ಶೀಟ್" : "Charge-sheeted", fmt(k.charge_sheeted)],
            [kn ? "ವಿಲೇವಾರಿ" : "Disposed", fmt(k.disposed)],
            [kn ? "ಈ ತಿಂಗಳ ಟಾಪ್ ವಲಯ" : "Top zone", k.top_zone_this_month || "—"],
          ],
          chartTitle: kn ? "FIR ಸಲ್ಲಿಕೆ - ಕಳೆದ 12 ತಿಂಗಳು" : "FIRs filed - last 12 months",
          bars: trend.map((t) => [t.month.slice(5), t.n]),
          listTitle: kn ? "ಟಾಪ್ ಜಿಲ್ಲೆಗಳು" : "Top districts by FIRs",
          list: (overview.hotspots_this_month || []).map((h) => [h.zone, fmt(h.n)]),
        };
      }
      case "open": {
        const statuses = (overview.by_status || []).slice(0, 4);
        return {
          title: kn ? "ಬಾಕಿ ಪ್ರಕರಣಗಳು" : "Open Cases", value: fmt(k.open_cases),
          substats: statuses.map((s) => [cap(s.status), fmt(s.n)]),
          chartTitle: kn ? "ಸ್ಥಿತಿಯ ಪ್ರಕಾರ ಪ್ರಕರಣಗಳು" : "Cases by status",
          bars: (overview.by_status || []).slice(0, 8).map((s) => [shortLabel(cap(s.status), 6), s.n]),
          listTitle: kn ? "ಪ್ರಮುಖ ಅಪರಾಧ ಪ್ರಕಾರಗಳು" : "Top crime types",
          list: (overview.crime_by_type || []).slice(0, 5).map((c) => [cap(c.crime_type), fmt(c.n)]),
        };
      }
      case "alerts": {
        const critical = alerts.filter((a) => a.z_score >= 4).length;
        const high = alerts.filter((a) => a.z_score >= 3 && a.z_score < 4).length;
        const medium = alerts.filter((a) => a.z_score < 3).length;
        return {
          title: kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು" : "Active Alerts", value: fmt(alerts.length),
          substats: [
            [kn ? "ನಿರ್ಣಾಯಕ" : "Critical", critical], [kn ? "ಹೆಚ್ಚು" : "High", high],
            [kn ? "ಮಧ್ಯಮ" : "Medium", medium], [kn ? "ಸರಾಸರಿ z" : "Avg z", alerts.length ? (alerts.reduce((s, a) => s + (a.z_score || 0), 0) / alerts.length).toFixed(2) : "0"],
          ],
          chartTitle: kn ? "ಎಚ್ಚರಿಕೆ z-ಸ್ಕೋರ್" : "Alert z-scores",
          bars: alerts.map((a) => [shortLabel(a.zone, 6), a.z_score]),
          listTitle: kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು" : "Active alerts",
          list: alerts.map((a) => [`${cap(a.crime_type)} · ${a.zone}`, `z=${a.z_score}`]),
        };
      }
      case "risk": {
        return {
          title: kn ? "ಅಗ್ರ ಅಪಾಯ ಸ್ಕೋರ್" : "Top Risk Score", value: topRisk ? `${topRisk.risk_score}%` : "—",
          substats: topRisk ? [
            [kn ? "ಶಂಕಿತ" : "Suspect", topRisk.full_name], [kn ? "ವಲಯ" : "Zone", topRisk.zone],
            [kn ? "ಹಿಂದಿನ ಪ್ರಕರಣಗಳು" : "Priors", topRisk.prior_count], [kn ? "ಅಲಿಯಾಸ್" : "Alias", topRisk.alias || "—"],
          ] : [],
          chartTitle: kn ? "ಅಗ್ರ ಅಪಾಯಕಾರಿ ಶಂಕಿತರು" : "Top risk offenders",
          bars: registry.slice(0, 8).map((r) => [shortLabel(r.full_name, 6), r.risk_score]),
          listTitle: kn ? "ಮುಂದಿನ ಅಗ್ರ ಅಪಾಯಗಳು" : "Next highest risk",
          list: registry.slice(1, 6).map((r) => [r.full_name, `${r.risk_score}%`]),
        };
      }
      case "links": {
        const links = related?.results?.[0]?.links || [];
        return {
          title: kn ? "ಅಡ್ಡ-ಪ್ರಕರಣ ಕೊಂಡಿಗಳು" : "Cross-case Links", value: fmt(links.length),
          substats: featuredLink ? [
            [kn ? "ಹೊಂದಾಣಿಕೆ ಸ್ಕೋರ್" : "Match score", featuredLink.score], [kn ? "ಹಂಚಿಕೆ ಸಂಪರ್ಕಗಳು" : "Shared contacts", featuredLink.shared_contact_count],
            [kn ? "ಅಡ್ಡ-ನಗರ" : "Cross-city", featuredLink.cross_city ? (kn ? "ಹೌದು" : "Yes") : (kn ? "ಇಲ್ಲ" : "No")], [kn ? "ತಿಂಗಳ ಹಿಂದೆ" : "Months ago", featuredLink.months_ago],
          ] : [],
          chartTitle: kn ? "ಕೊಂಡಿ ಹೊಂದಾಣಿಕೆ ಸ್ಕೋರ್‌ಗಳು" : "Link match scores",
          bars: links.map((l) => [shortLabel(l.full_name, 6), Math.round(l.score * 100)]),
          listTitle: kn ? "ಬಲವಾದ ಕೊಂಡಿಗಳು" : "Strongest links",
          list: links.map((l) => [`${seedName} ↔ ${l.full_name} (${l.city})`, l.score]),
        };
      }
      case "patterns": {
        const top = [...patterns].sort((a, b) => b.size - a.size).slice(0, 8);
        const crimeCounts = {};
        for (const p of patterns) for (const c of (p.crime_types || [])) crimeCounts[c] = (crimeCounts[c] || 0) + 1;
        const topCrimes = Object.entries(crimeCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);
        return {
          title: kn ? "ಪಟ್ಟಿ ಮಾದರಿಗಳು" : "Patterns Indexed", value: fmt(patterns.length),
          substats: [
            [kn ? "ದೊಡ್ಡ ಕ್ಲಸ್ಟರ್" : "Largest cluster", fmt(top[0]?.size || 0)],
            [kn ? "ಒಟ್ಟು ಗುಂಪುಗಳು" : "Total clusters", patterns.length],
            [kn ? "ಒಳಗೊಂಡ ವಲಯಗಳು" : "Zones covered", new Set(patterns.flatMap((p) => p.zones || [])).size],
            [kn ? "ಅಪರಾಧ ಪ್ರಕಾರಗಳು" : "Crime types", new Set(patterns.flatMap((p) => p.crime_types || [])).size],
          ],
          chartTitle: kn ? "ಕ್ಲಸ್ಟರ್ ಗಾತ್ರಗಳು" : "Cluster sizes",
          bars: top.map((p) => [`C${p.cluster_id}`, p.size]),
          listTitle: kn ? "ಪ್ರಮುಖ ಅಪರಾಧ ಪ್ರಕಾರಗಳು" : "Top crime types",
          list: topCrimes.map(([c, n]) => [cap(c), `${n} ${kn ? "ಕ್ಲಸ್ಟರ್" : "clusters"}`]),
        };
      }
      default: return null;
    }
  }

  function openTile(key) {
    if (activeTile === key) { setActiveTile(null); return; }
    setActiveTile(key);
    setTimeout(() => drillRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  const drill = activeTile ? buildDrill(activeTile) : null;

  if (err) return (
    <div className="bx-main"><div className="bx-graph-empty">
      {kn ? `ಬ್ಯಾಕೆಂಡ್ ${API} ತಲುಪಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.` : `Could not reach the backend at ${API}.`}
    </div></div>
  );
  if (!overview) return <div className="bx-main"><div className="bx-graph-empty">{kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading…"}</div></div>;

  return (
    <>
      <div className="bx-main">
        <div className="bx-gpanel">
          {graph?.nodes ? <NetworkGraph data={graph} /> : <div className="bx-graph-empty">{kn ? "ಜಾಲ ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading network…"}</div>}
          <div className="bx-gmeta">{graph ? `${graph.stats?.node_count ?? graph.nodes?.length ?? 0} nodes · ${graph.stats?.edge_count ?? graph.edges?.length ?? 0} links${graph.brain_banner ? " · 1 cross-case" : ""}` : ""}</div>
          <button className="bx-askantar" onClick={() => router.push("/antar")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 5h16v11H8l-4 4z" strokeLinejoin="round" /></svg>
            {kn ? "Antar ಕೇಳಿ" : "Ask Antar"}
          </button>
          <button className="bx-expand" onClick={() => router.push("/antarBrain/structure")}
                  title={kn ? "3D ರಚನೆಯಲ್ಲಿ ವಿಸ್ತರಿಸಿ" : "Expand to 3D structure"}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" /></svg>
            {kn ? "3D ವೀಕ್ಷಣೆ" : "3D View"}
          </button>
          <div className="bx-depth">
            <span>{kn ? "ಆಳ" : "Depth"}</span>
            <div className="h" role="group" aria-label="Graph depth">
              {[1, 2, 3].map((d) => <button key={d} className={depth === d ? "on" : ""} onClick={() => setDepth(d)}>{d}</button>)}
            </div>
            <span style={{ opacity: 0.6 }}>{kn ? "ಹಾಪ್ಸ್" : "hops"}</span>
          </div>
          <div className="bx-legend">
            <span><i style={{ background: "#3B82F6" }} />{kn ? "ಶಂಕಿತ (ಬೀಜ)" : "suspect (seed)"}</span>
            <span><i style={{ background: "#33456e" }} />{kn ? "ಸಹಚರ" : "associate"}</span>
            <span><i style={{ background: "#FFB020" }} />{kn ? "ಅಡ್ಡ-ಪ್ರಕರಣ" : "cross-case (Second Brain)"}</span>
          </div>
        </div>

        <div className="bx-right">
          <div className="bx-secttl">{kn ? "ಸಮಗ್ರ ನೋಟ · ವಿವರಕ್ಕೆ ಟೈಲ್ ಒತ್ತಿ" : "Overview · tap a tile for detail"}</div>
          <div className="bx-tiles">
            {tiles.map((t) => (
              <button key={t.key} className={`bx-tile ${activeTile === t.key ? "active" : ""}`} onClick={() => openTile(t.key)}
                      aria-expanded={activeTile === t.key} aria-controls="bx-drill-region">
                <span className="chev">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </span>
                <div className="l">{t.label}</div>
                <div className={`v ${t.cls}`}>{t.value}</div>
              </button>
            ))}
          </div>

          <div className="bx-feed" aria-live="polite">
            <div className="br-act-hdr">
              <span className="t">{kn ? "ಮೆದುಳು ಚಟುವಟಿಕೆ" : "Brain Activity"}</span>
              <span className="bx-live"><span className="d" />LIVE</span>
            </div>
            {linkage && linkage.candidates?.[0] && (
              <div className="bx-ev xc" style={{ borderLeft: "3px solid #22e6f0", background: "rgba(34,230,240,0.05)" }}>
                <div className="sp" />
                <div className="bx-evhead">
                  <span style={{ color: "#22e6f0", fontWeight: 700 }}>{kn ? "A3 MO ಪ್ರಕರಣ-ಹೊಂದಾಣಿಕೆ · " : "A3 MO Case-Matcher · "} {linkage.fir_id}</span>
                  <span style={{ fontSize: "11px", color: "#aaa" }}>{linkage.candidates[0].confidence} {kn ? "ವಿಶ್ವಾಸಾರ್ಹತೆ" : "Confidence"} ({linkage.candidates[0].total_score} pts)</span>
                </div>
                <p style={{ margin: "4px 0", color: "#ddd" }}><b>{linkage.candidates[0].linked_fir_id}</b> ({linkage.candidates[0].district} · {linkage.candidates[0].crime_type})</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                  {linkage.candidates[0].reason_chips?.map((rc, i) => (
                    <span key={i} style={{ background: "rgba(255,255,255,0.08)", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", color: "#22e6f0" }}> {rc}</span>
                  ))}
                </div>
              </div>
            )}
            {related?.results?.[0]?.banner && (
              <div className="bx-ev xc">
                <div className="sp" />
                <div className="bx-evhead">
                  <span>{kn ? "ಎರಡನೇ ಮೆದುಳು · ಅಡ್ಡ-ಪ್ರಕರಣ ಕೊಂಡಿ" : "Second Brain · cross-case link"}</span>
                  <a onClick={() => openTile("links")}>{kn ? "ಸಂಪರ್ಕ ನೋಡಿ →" : "View connection →"}</a>
                </div>
                <p>{related.results[0].banner.replace(/^\s*/, "")}</p>
              </div>
            )}
            {live.map((e, i) => (
              <div className="bx-ev" key={i}>
                <div className="br-event-bd">
                  <p>{cap(e.crime_type)} · {e.zone} - {e.message}</p>
                  {e.agent && e.output_digest && (
                    <p>{e.agent?.toUpperCase()} · {e.step} - {e.output_digest}</p>
                  )}
                </div>
                <div className="ts">{kn ? "ಈಗ" : "just now"}</div>
              </div>
            ))}
            {activity.map((a, i) => (
              <div className="bx-ev" key={"act" + i}><p>{a.label || a.detail}</p><div className="ts">{a.date}</div></div>
            ))}
            {!related?.results?.[0]?.banner && live.length === 0 && activity.length === 0 && (
              <div className="ts">{kn ? "ಚಟುವಟಿಕೆಗಾಗಿ ಕಾಯಲಾಗುತ್ತಿದೆ…" : "Waiting for activity…"}</div>
            )}
          </div>
        </div>
      </div>

      <section className={`bx-drill ${drill ? "open" : ""}`} id="bx-drill-region" ref={drillRef}>
        {drill && (
          <>
            <div className="bx-dh">
              <span className="dt">{drill.title}</span>
              <span className="dv">{drill.value}</span>
              <button className="dclose" onClick={() => setActiveTile(null)}>{kn ? "ಮುಚ್ಚಿ" : "Close"} </button>
            </div>
            <div className="bx-substats">
              {drill.substats.map(([l, v], i) => <div className="bx-ss" key={i}><div className="l">{l}</div><div className="v">{v}</div></div>)}
            </div>
            <div className="bx-dgrid">
              <div className="bx-dcard">
                <h4>{drill.chartTitle}</h4>
                <div className="bx-bars">
                  {drill.bars.length > 0 ? (() => {
                    const max = Math.max(...drill.bars.map((b) => Math.abs(b[1]) || 0), 1);
                    return drill.bars.map(([l, v], i) => (
                      <div className="bar" key={i} style={{ height: `${Math.max(4, (Math.abs(v) / max) * 100)}%` }}><span>{l}</span></div>
                    ));
                  })() : <div className="ts" style={{ color: "var(--muted)" }}>{kn ? "ಡೇಟಾ ಇಲ್ಲ" : "No data"}</div>}
                </div>
              </div>
              <div className="bx-dcard bx-dlist">
                <h4>{drill.listTitle}</h4>
                {drill.list.length > 0 ? drill.list.map(([l, v], i) => (
                  <div className="row" key={i}><span>{l}</span><b>{v}</b></div>
                )) : <div className="ts" style={{ color: "var(--muted)" }}>{kn ? "ಡೇಟಾ ಇಲ್ಲ" : "No data"}</div>}
              </div>
            </div>
          </>
        )}
      </section>
    </>
  );
}


