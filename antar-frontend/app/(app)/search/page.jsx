"use client";

import { useCallback, useEffect, useMemo, useRef, useState, Suspense } from "react";
import { fetchAPI } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { useLang } from "@/components/Providers";
import { RefBadge } from "@/components/RefStrip";
import { Mic, MicOff, X, ShieldCheck } from "lucide-react";
import ProposeAction from "@/components/ProposeAction";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

// Every chip maps to a REAL backend field scope (/api/profile/search?field=)
const FILTERS = [
  { key: "all", en: "All", kn: "ಎಲ್ಲಾ" },
  { key: "name", en: "Name", kn: "ಹೆಸರು" },
  { key: "alias", en: "Alias", kn: "ಅಡ್ಡಹೆಸರು" },
  { key: "father", en: "Father (s/o)", kn: "ತಂದೆ" },
  { key: "phone", en: "Phone", kn: "ಫೋನ್" },
];

const EXAMPLES = ["Raju", "Yellappa", "Tiger", "Manju"];

const initials = (name) => (name || "?").split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
const cap = (s) => (s || "").replace(/_/g, " ");

function HighlightName({ name, query }) {
  if (!query) return <>{name}</>;
  const parts = String(name).split(new RegExp(`(${query})`, 'gi'));
  return <>{parts.map((p, i) => p.toLowerCase() === query.toLowerCase() ? <span key={i} style={{ color: "var(--cyan)", fontWeight: 700 }}>{p}</span> : p)}</>;
}


// Explain WHY a result matched - officers should never have to guess.
function matchWhy(r) {
  const field = { full_name: 'name', alias: 'alias', father_name: 'father', phone_hash: 'phone' }[r.match_field] || r.match_field;
  switch (r.match_method) {
    case 'exact': return { cls: 'ex', txt: `exact on ${field}` };
    case 'phone_exact': return { cls: 'ex', txt: `exact on phone` };
    case 'jaro_winkler': return { cls: 'fz', txt: `typo on ${field}` };
    case 'soundex': return { cls: 'ph', txt: `phonetic on ${field}` };
    default: return null;
  }
}
function tier(score) { return score >= 70 ? "HIGH" : score >= 40 ? "MED" : "LOW"; }
function tierCls(score) { return score >= 70 ? "h" : score >= 40 ? "m" : "l"; }

function useDebounce(val, ms) {
  const [d, setD] = useState(val);
  useEffect(() => { const t = setTimeout(() => setD(val), ms); return () => clearTimeout(t); }, [val, ms]);
  return d;
}

function SearchContent() {
  const router = useRouter();
  const sp = useSearchParams();
  const { lang } = useLang();
  const kn = lang === "kn";

  const [role, setRoleState] = useState("Officer");
  const [trueAdmin, setTrueAdmin] = useState(false);
  const [showOsintInfo, setShowOsintInfo] = useState(false);
  const [profileTab, setProfileTab] = useState("details");
  const [osintConsentOpen, setOsintConsentOpen] = useState(true); // consent gate before OSINT is ever enabled
  useEffect(() => {
            function checkRole() {
      try {
        const s = JSON.parse(sessionStorage.getItem("antar_session") || "null");
        if (s?.role) {
          setTrueAdmin(s.role === "Admin");
          setRoleState(s.role || "Officer");
        }
      } catch {}
    }
    checkRole();
    window.addEventListener("antar-role", checkRole);
    window.addEventListener("storage", checkRole);
    return () => {
      window.removeEventListener("antar-role", checkRole);
      window.removeEventListener("storage", checkRole);
    };
  }, []);

    function setRole(next) {
    setRoleState(next);
  }

  const isAdmin = role === "Admin";
  // Mirrors INSPECTOR_PLUS_ROLES in app/api/hypothesis.py. Login only issues Officer or
  // Admin, so in practice only Admins can review - offering Officers buttons the backend
  // will always refuse is what produced the RBAC error overlay.
  const canReviewHypotheses = ["inspector", "dcp", "acp", "admin", "commissioner", "superintendent", "sub-inspector"]
    .includes(String(role || "").toLowerCase());
  // OSINT was consent-gated for every role before the Search redesign, which quietly made
  // it Admin-only. Every OSINT query is audit-logged and /api/osint has no role guard, so
  // the lock was UI-only. Flip to true to restore the Admin-only restriction.
  const OSINT_ADMIN_ONLY = false;
  const osintAllowed = trueAdmin || !OSINT_ADMIN_ONLY;

  const [query, setQuery] = useState(sp?.get("q") || "");
  const [filterType, setFilterType] = useState("all");
  const debounced = useDebounce(query, 350);

  const [recording, setRecording] = useState(false);
  const recRef = useRef(null);

  const toggleVoice = useCallback(() => {
    if (recording && recRef.current) {
      recRef.current.stop();
      setRecording(false);
      return;
    }
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) {
      alert(kn ? "ನಿಮ್ಮ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಇನ್ಪುಟ್ ಬೆಂಬಲಿಸುವುದಿಲ್ಲ" : "Voice input not supported in this browser.");
      return;
    }
    const rec = new Speech();
    rec.lang = kn ? "kn-IN" : "en-IN";
    rec.interimResults = false;
    rec.onresult = (e) => {
      const transcript = e.results[0]?.[0]?.transcript;
      if (transcript) setQuery((prev) => (prev ? prev + " " + transcript : transcript));
      setRecording(false);
    };
    rec.onerror = () => setRecording(false);
    rec.onend = () => setRecording(false);
    recRef.current = rec;
    rec.start();
    setRecording(true);
  }, [recording, kn]);

  const [results, setResults] = useState(null); // null = loading
  const [isSearch, setIsSearch] = useState(false); // true = fuzzy search, false = registry
  const [selectedId, setSelectedId] = useState(null);
  const [profile, setProfile] = useState(null);
  const [assoc, setAssoc] = useState([]);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // OSINT (admin)
  const [osint, setOsint] = useState(null);
  const [osintLoading, setOsintLoading] = useState(false);
  const [reconData, setReconData] = useState(null);
  const [reconTab, setReconTab] = useState("maltego"); // "maltego" | "telecom" | "sherlock" | "bbot"

  // Layer 5 Unknown-First & Identity Hypotheses
  const [unknownDiscovery, setUnknownDiscovery] = useState(null);
  const [identityHypotheses, setIdentityHypotheses] = useState([]);
  const [trackToast, setTrackToast] = useState(null);
  const [watchRequest, setWatchRequest] = useState(false);   // HITL: request a watchlist entry

  const flashToast = useCallback((text, tone = "ok") => {
    setTrackToast({ text, tone });
    setTimeout(() => setTrackToast(null), tone === "ok" ? 4000 : 6000);
  }, []);

  const trackUnknownLead = useCallback((leadQuery) => {
    fetchAPI(`/api/profile/track_unknown`, {
      method: "POST",
      body: JSON.stringify({ query: leadQuery, field: filterType }),
    })
      .then((d) => flashToast(` Tracked Unknown Lead (${d.gap_id}) in Second Brain`))
      .catch((err) => flashToast(err.message || "Could not track lead", "error"));
  }, [filterType, flashToast]);

  const handleHypothesisAction = useCallback((hypId, action) => {
    const s = JSON.parse(sessionStorage.getItem("antar_session") || "{}");
    const body = { officer: s.officer || "Unknown", role: s.role || "Officer", reason: "Manual review via UI" };
    fetchAPI(`/api/hypothesis/${hypId}/${action}`, { method: "POST", body: JSON.stringify(body) })
      .then(() => {
        setIdentityHypotheses((prev) => prev.filter((h) => h.hypothesis_id !== hypId));
        flashToast(`Identity Hypothesis ${action.toUpperCase()}`);
      })
      .catch((err) => {
        // Without this catch a refused review surfaced as a Next.js "Unhandled Runtime
        // Error" overlay. The hypothesis stays in the list - nothing changed server-side.
        if (err.status === 409 && err.detail?.verdict) {
          flashToast(`Adversarial review: ${err.detail.verdict} - ${err.detail.verdict_reason || "acknowledgement required"}`, "warn");
        } else {
          flashToast(err.message || `Could not ${action} hypothesis`, "error");
        }
      });
  }, [flashToast]);

  // ── Load list: registry when empty, fuzzy search when typing.
  useEffect(() => {
    let alive = true;
    const q = debounced.trim();
    if (!q) {
      setIsSearch(false);
      setUnknownDiscovery(null);
      fetchAPI(`/api/profile/registry?min_priors=1&limit=30`)
        .then((d) => {
          if (!alive) return;
          setResults((d.offenders || []).map((o) => ({ ...o, address_zone: o.zone })));
        })
        .catch(() => alive && setResults([]));
    } else {
      setIsSearch(true);
      const fieldQ = filterType !== "all" ? `&field=${filterType}` : "";
      fetchAPI(`/api/profile/search?q=${encodeURIComponent(q)}&limit=25&threshold=0.55${fieldQ}`)
        .then((d) => {
          if (!alive) return;
          setResults(d.hits || []);
          setUnknownDiscovery(d.unknown_discovery || ((!d.hits || d.hits.length === 0) ? {
            message: `No exact verified profile for "${q}". Generating synthetic unknown-first lead hypothesis.`,
            nearest_neighbors: [],
          } : null));
          setIdentityHypotheses(d.identity_hypotheses || []);
        })
        .catch(() => alive && setResults([]));
    }
    return () => { alive = false; };
  }, [debounced, filterType]);

  // Auto-select first result whenever the list changes
  useEffect(() => {
    if (results && results.length && !results.find((r) => r.suspect_id === selectedId)) {
      setSelectedId(results[0].suspect_id);
    }
    if (results && results.length === 0) { setSelectedId(null); setProfile(null); }
  }, [results]); // eslint-disable-line

  useEffect(() => {
    function handleKeyDown(e) {
      if (!results || results.length === 0) return;
      // Dont steal focus from inputs
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const idx = results.findIndex(r => r.suspect_id === selectedId);
        let nextIdx = idx;
        if (e.key === 'ArrowDown') nextIdx = Math.min(results.length - 1, idx + 1);
        if (e.key === 'ArrowUp') nextIdx = Math.max(0, idx - 1);
        if (nextIdx !== idx && nextIdx >= 0) {
          setSelectedId(results[nextIdx].suspect_id);
          const el = document.getElementById(`sx-row-${results[nextIdx].suspect_id}`);
          if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [results, selectedId]);


  // ── Load profile detail + associates on select ──
  useEffect(() => {
    if (!selectedId) return;
    let alive = true;
    setLoadingProfile(true);
    const row = results?.find((r) => r.suspect_id === selectedId) || {};
    Promise.all([
      fetchAPI(`/api/profile/${selectedId}`).catch(() => null),
      fetchAPI(`/api/graph/${selectedId}?depth=1`).catch(() => null),
    ]).then(([p, g]) => {
      if (!alive) return;
      setProfile(p?.suspect_id ? { ...row, ...p } : { ...row });
      setAssoc((g?.nodes || []).filter((n) => n.type !== "seed"));
      setLoadingProfile(false);
    });
    return () => { alive = false; };
  }, [selectedId]); // eslint-disable-line

  // ── OSINT run (admin) ──
  const runOsint = useCallback(() => {
    const q = query.trim() || profile?.full_name || "";
    if (!q) return;
    setOsintLoading(true);
    Promise.all([
      fetchAPI(`/api/osint/?entity=${encodeURIComponent(q)}`).catch(() => ({ claims: [] })),
      fetchAPI(`/api/osint/recon?entity=${encodeURIComponent(q)}`).catch(() => null),
    ])
      .then(([d, r]) => {
        setOsint({ q, claims: d.claims || [] });
        setReconData(r);
      })
      .finally(() => setOsintLoading(false));   // was never reset: stuck on "Scanning…"
  }, [query, profile]);

  // Short alias for the selected profile - the detail pane references it ~60 times.
  const p = profile;
  // Verified internal record the OSINT workspace is anchored to. Pre-redesign this was
  // results[0] (OSINT was its own page); OSINT now lives in the selected profile's tab,
  // so it must follow the selection rather than whichever row happens to sort first.
  const anchor = p || results?.find((r) => r.suspect_id === selectedId) || null;

  // Everything below is read from the profile / registry payloads. Fields the API does
  // not provide (age, gender, police station, activity hours) are NOT shown - the old
  // pane printed "17:00 – 22:00" and "<zone> PS" for every suspect.
  const row = results?.find((r) => r.suspect_id === selectedId) || null;
  const rec = p ? {
    zone: p.address_zone || p.zone || row?.address_zone || row?.zone || null,
    priors: p.prior_count ?? row?.prior_count ?? null,
    firCount: row?.fir_count ?? null,
    linkedCases: Number((p.mo_summary || "").match(/(\d+)\s+linked case/i)?.[1]) || null,
    lastFirDays: p.raw_factors?.recency_days ?? null,
    status: cap(p.arrest_status) || (p.mo_summary || "").match(/arrest status ([\w_]+)/i)?.[1]?.replace(/_/g, " ") || null,
    moText: (p.mo_summary || "").replace(/\s*Prior count \d+;\s*arrest status [\w_]+\.?/i, "").trim(),
    contrib: [
      // No count here on purpose: profile_agent's risk model and its MO summary use two
      // different case-linkage lookups (e.g. 46 vs 69 for S0041). Showing both numbers on
      // one screen reads as an error, so the key figures carry the MO count only.
      ["frequency", kn ? "ಆಗಾಗ್ಗೆ ಅಪರಾಧ" : "Frequent offending", null],
      ["recency", kn ? "ಇತ್ತೀಚಿನ ಚಟುವಟಿಕೆ" : "Recent activity", p.raw_factors?.recency_days != null ? (kn ? `${p.raw_factors.recency_days} ದಿನಗಳ ಹಿಂದೆ` : `last FIR ${p.raw_factors.recency_days}d ago`) : null],
      ["severity", kn ? "ಗಂಭೀರ ಅಪರಾಧಗಳು" : "Serious offences", null],
      ["centrality", kn ? "ಜಾಲದ ಕೇಂದ್ರ" : "Network centrality", null],
    ].map(([k, label, detail]) => ({ k, label, detail, pts: Math.round(p.risk_attributions?.[k] ?? (p.factors?.[k] || 0) * 25) })),
    strongMatches: (p.similar_cases || []).filter((c) => (c.score || 0) >= 0.25),
  } : null;
  return (
    <div className="sx-page">
      {p && (
        <ProposeAction open={watchRequest} onClose={() => setWatchRequest(false)} type="watchlist_add" kn={kn}
          defaults={{ watch_type: "entity", target: p.suspect_id, label: `Watch · ${p.full_name} (${p.suspect_id})` }}
          evidence={[
            { label: kn ? "ಅಪಾಯ ಅಂಕ" : "Risk score", value: `${Math.round(p.risk_score || 0)}/100` },
            rec?.linkedCases != null && { label: kn ? "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು" : "Linked cases", value: String(rec.linkedCases) },
            rec?.lastFirDays != null && { label: kn ? "ಕೊನೆಯ FIR" : "Last FIR", value: `${rec.lastFirDays} days ago` },
            rec?.status && { label: kn ? "ಸ್ಥಿತಿ" : "Status", value: rec.status },
            (p.associates?.length ?? 0) > 0 && { label: kn ? "ಸಹಚರರು" : "Associates", value: String(p.associates.length) },
          ].filter(Boolean)} />
      )}
      <div className="sx-md">
        {/* LEFT: search + results list */}
        <div className="sx-listpanel">
          <div className="sx-searchwrap">
            <div className="sx-searchbar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" strokeLinecap="round" /></svg>
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={kn ? "ಹೆಸರು, ಅಡ್ಡಹೆಸರು, ಫೋನ್, ನಂ.ತಟ್ಟೆ…" : "Name, alias, phone, vehicle plate…"} aria-label={kn ? "ಶಂಕಿತರನ್ನು ಹುಡುಕಿ" : "Search suspects"} />
              <button type="button" className="clr" onClick={toggleVoice} title={recording ? "Stop listening" : "Speak suspect name"} style={{ background: recording ? "rgba(239,68,68,0.2)" : "transparent", color: recording ? "#EF4444" : "#22E6F0", marginRight: query ? "4px" : "0" }}>
                {recording ? <MicOff size={14} /> : <Mic size={14} />}
              </button>
              {query && <button className="clr" onClick={() => setQuery("")} aria-label="Clear"></button>}
            </div>
            <div className="sx-fchips" style={{ display: "flex", flexWrap: "wrap", alignItems: "center" }}>
              {FILTERS.map((f) => <button key={f.key} className={filterType === f.key ? "on" : ""} onClick={() => setFilterType(f.key)}>{kn ? f.kn : f.en}</button>)}
              {osintAllowed && (
                <button type="button"
                  className={profileTab === "osint" ? "on" : ""}
                  onClick={() => {
                    if (profileTab === "osint") { setProfileTab("details"); return; }
                    if (!selectedId && results?.length) setSelectedId(results[0].suspect_id);
                    setProfileTab("osint");
                  }}
                  title={kn ? "ಮುಕ್ತ-ಮೂಲ ಗುಪ್ತಚರ - ಎಲ್ಲಾ ಪ್ರಶ್ನೆಗಳು ಲಾಗ್ ಆಗುತ್ತವೆ" : "Open-source intelligence - unverified, every query is audit-logged"}
                  style={{ marginLeft: "auto", color: "var(--osint)", borderColor: "var(--osint)" }}>
                  {profileTab === "osint"
                    ? (kn ? "OSINT ಮುಚ್ಚಿ" : "Close OSINT")
                    : osintConsentOpen ? (kn ? "OSINT ಸಕ್ರಿಯಗೊಳಿಸಿ" : "Enable OSINT (Preview)") : "OSINT"}
                </button>
              )}
            </div>
            <div className="sx-enginehint">
              {kn ? "ಫಝಿ + ಧ್ವನಿ ಹುಡುಕಾಟ - ಕಾಗುಣಿತ ವ್ಯತ್ಯಾಸ ಸರಿ (Yellappa ≈ Yellapa)" : "Fuzzy + phonetic engine - typos & spelling variants OK (Yellappa ≈ Yellapa ≈ Ylappa)"}
            </div>
          </div>

          {trackToast && (() => {
            const c = { ok: "#18D69A", warn: "#FFB020", error: "#FF3B30" }[trackToast.tone] || "#18D69A";
            return (
              <div role="status" style={{ padding: "10px 14px", margin: "10px", borderRadius: "8px", background: `${c}2E`, border: `1px solid ${c}`, color: c, fontWeight: 700, fontSize: "12px" }}>
                {trackToast.text}
              </div>
            );
          })()}

          {identityHypotheses.length > 0 && (
            <div style={{ margin: "10px", padding: "12px", background: "rgba(176,38,255,0.08)", border: "1px solid rgba(176,38,255,0.4)", borderRadius: "8px" }}>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#B026FF", marginBottom: "6px" }}>
                INFERRED CROSS-SOURCE IDENTITY HYPOTHESES · REQUIRES INSPECTOR REVIEW
              </div>
              {identityHypotheses.slice(0, 2).map((h) => (
                <div key={h.hypothesis_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px", background: "rgba(0,0,0,0.3)", borderRadius: "6px", marginBottom: "6px", fontSize: "12px" }}>
                  <div>
                    <span style={{ fontWeight: 700, color: "#E2E8F0" }}>{h.entity_a.name} ({h.entity_a.id})</span>
                    {" ≈ "}
                    <span style={{ fontWeight: 700, color: "#E2E8F0" }}>{h.entity_b.name} ({h.entity_b.id})</span>
                    <div style={{ fontSize: "11px", color: "#94A3B8" }}>
                      Confidence: {Math.round(h.confidence * 100)}% · {h.reasons.join(", ")}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "6px" }}>
                    {[["confirm", "Confirm", "24,214,154", "#18D69A"], ["reject", "Reject", "255,59,48", "#FF3B30"]].map(([action, label, rgb, hex]) => (
                      <button key={action} disabled={!canReviewHypotheses}
                        title={canReviewHypotheses ? undefined : (kn ? "ಇನ್ಸ್‌ಪೆಕ್ಟರ್ ಅಥವಾ ಮೇಲಿನ ಶ್ರೇಣಿ ಅಗತ್ಯ" : `Inspector or higher rank required (you are signed in as ${role})`)}
                        onClick={() => handleHypothesisAction(h.hypothesis_id, action)}
                        style={{ padding: "4px 8px", borderRadius: "4px", background: `rgba(${rgb},0.2)`, border: `1px solid ${hex}`, color: hex, fontSize: "11px", fontWeight: 700, cursor: canReviewHypotheses ? "pointer" : "not-allowed", opacity: canReviewHypotheses ? 1 : 0.45 }}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="sx-sortrow">
            <span style={{ display: "inline-flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              {results && results.length > 0 && <RefBadge tag="K" />}
              {results
                ? `${results.length} ${kn ? "ಫಲಿತಾಂಶ" : "results"} · ${isSearch ? (kn ? "ಫಝಿ ಹೊಂದಾಣಿಕೆ" : "fuzzy + phonetic match") : (kn ? "ನೋಂದಣಿ" : "registry")}${isSearch && filterType !== "all" ? ` · ${FILTERS.find((f) => f.key === filterType)?.[kn ? "kn" : "en"]} ${kn ? "ಮಾತ್ರ" : "only"}` : ""}`
                : (kn ? "ಲೋಡ್…" : "loading…")}
            </span>
            <span className="sv">{kn ? "ಅಪಾಯ ↓" : "Risk ↓"}</span>
          </div>

          <div className="sx-results" role="list">
            {results === null && <div className="sx-listloading"><div className="signal-pulse" style={{ width: 140 }} /></div>}
            {results && results.length === 0 && (
              <div className="sx-nomatch">
                <p>{kn ? "ಯಾವುದೇ ದಾಖಲೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ." : "No matching records found."}</p>
                {unknownDiscovery && (
                  <div style={{ margin: "14px 0", padding: "14px", background: "rgba(34,230,240,0.08)", border: "1px solid #22E6F0", borderRadius: "8px", textAlign: "left" }}>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#22E6F0", marginBottom: "8px" }}>
                      {kn ? "ಅಜ್ಞಾತ ಲೀಡ್ ಅನ್ವೇಷಣೆ ಪ್ರೋಟೋಕಾಲ್ ಸಕ್ರಿಯ" : "UNKNOWN-FIRST DISCOVERY PROTOCOL ACTIVE"}
                    </div>
                    <div style={{ fontSize: "12px", color: "#E2E8F0", marginBottom: "10px" }}>
                      {unknownDiscovery.message}
                    </div>
                    {unknownDiscovery.nearest_neighbors?.length > 0 && (
                      <div style={{ fontSize: "11px", color: "#94A3B8", marginBottom: "8px" }}>
                        <b>Phonetic Nearest Neighbors:</b> {unknownDiscovery.nearest_neighbors.map((n) => `${n.full_name} (${Math.round(n.match_score * 100)}%)`).join(", ")}
                      </div>
                    )}
                    <button
                      onClick={() => trackUnknownLead(query)}
                      style={{ padding: "6px 12px", borderRadius: "6px", background: "#22E6F0", color: "#0A0E17", fontWeight: 700, fontSize: "12px", border: "none", cursor: "pointer" }}
                    >
                      + {kn ? "ಈ ಅಜ್ಞಾತ ಲೀಡ್ ಅನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ" : "Track this Unknown Lead in Second Brain"}
                    </button>
                  </div>
                )}
                <p className="tip">{filterType !== "all"
                  ? (kn ? `"${FILTERS.find((f) => f.key === filterType)?.kn}" ಫಿಲ್ಟರ್ ಸಕ್ರಿಯ - "ಎಲ್ಲಾ" ಪ್ರಯತ್ನಿಸಿ.` : `The "${FILTERS.find((f) => f.key === filterType)?.en}" filter is active - try "All".`)
                  : (kn ? "ಕಡಿಮೆ ಅಕ್ಷರ ಅಥವಾ ಅಡ್ಡಹೆಸರು ಪ್ರಯತ್ನಿಸಿ:" : "Try fewer letters, an alias, or one of these:")}</p>
                <div className="sx-try">
                  {filterType !== "all" && <button onClick={() => setFilterType("all")}>{kn ? "ಎಲ್ಲಾ ಕ್ಷೇತ್ರ" : "Search all fields"}</button>}
                  {EXAMPLES.map((e) => <button key={e} onClick={() => setQuery(e)}>{e}</button>)}
                </div>
              </div>
            )}
            {results?.map((r) => {
              const t = tierCls(r.risk_score || 0);
              const why = isSearch ? matchWhy(r, kn) : null;
              return (
                <div key={r.suspect_id} style={{ display: "flex", flexDirection: "column" }}>
                  <button
                    id={`sx-row-${r.suspect_id}`}
                    role="listitem"
                    className={`sx-rrow ${selectedId === r.suspect_id ? "active" : ""}`}
                    onClick={() => setSelectedId(selectedId === r.suspect_id ? null : r.suspect_id)}
                    style={{ borderBottom: selectedId === r.suspect_id ? "none" : "" }}
                  >
                    <span className={`sx-rav r-${t}`}>{initials(r.full_name)}</span>
                    <span className="sx-rbody">
                      <span className="nm"><HighlightName name={r.full_name} query={debounced} /></span>
                      <span className="al">{r.alias ? `alias "${r.alias}" · ` : ""}{r.suspect_id}</span>
                      <span className="mt">{r.address_zone || r.zone}{why ? <span className={`sx-why ${why.cls}`}>{why.txt}</span> : null}</span>
                    </span>
                    <span className="sx-rright">
                      <span className={`pip p-${t}`}>{tier(r.risk_score || 0)}</span>
                      <span className="fc">{r.prior_count ?? 0} {kn ? "FIR" : "FIRs"}</span>
                    </span>
                  </button>

                  {/* Minimalist Inline Evidentiary Dossier */}
                  {selectedId === r.suspect_id && (
                    <div style={{
                      margin: "0 4px 10px 4px",
                      padding: "16px",
                      background: (r.risk_score || 0) >= 70 ? "#050505" : "rgba(11,18,32,0.92)",
                      border: (r.risk_score || 0) >= 70 ? "1px solid rgba(239, 68, 68, 0.85)" : "1px solid rgba(255,255,255,0.15)",
                      borderRadius: "0 0 12px 12px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "12px",
                      animation: "fadeRise 0.2s ease-out"
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontSize: "11px", fontWeight: 600, color: (r.risk_score || 0) >= 70 ? "#EF4444" : "rgba(255,255,255,0.9)", fontFamily: "Chakra Petch" }}>
                            {kn ? "ಸೆಕ್ಷನ್ 91 ಸಾಕ್ಷ್ಯ ಆಡಿಟ್ ಡಾಸಿಯರ್" : "statutory § 91 evidentiary dossier"}
                          </span>
                          <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.7)", fontFamily: "JetBrains Mono" }}>
                            {kn ? "ಪರಿಶೀಲಿಸಿದ ಹೊಂದಾಣಿಕೆ" : "verified match"}
                          </span>
                        </div>
                        <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", fontFamily: "JetBrains Mono" }}>
                          id: <b style={{ color: "rgba(255,255,255,0.8)" }}>{r.suspect_id}</b>
                        </div>
                      </div>

                      {why && (
                        <div style={{ padding: "8px 10px", borderRadius: "6px", background: "rgba(255,255,255,0.03)", borderLeft: `3px solid ${(r.risk_score || 0) >= 70 ? "#EF4444" : "rgba(255,255,255,0.3)"}`, fontSize: "11.5px", color: "rgba(255,255,255,0.8)" }}>
                          <b>{kn ? "ಹೊಂದಾಣಿಕೆ ಕಾರಣ:" : "match justification:"}</b> {why.txt.toLowerCase()} ({kn ? "ಕ್ಷೇತ್ರ:" : "field:"} <code style={{ color: "rgba(255,255,255,0.9)" }}>{r.match_field || "full_name"}</code>)
                        </div>
                      )}

                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "8px" }}>
                        <div style={{ background: "rgba(255,255,255,0.02)", padding: "8px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.05)" }}>
                          <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.5)", fontFamily: "JetBrains Mono" }}>{kn ? "ಅಪಾಯ ಸೂಚ್ಯಂಕ" : "risk index"}</div>
                          <div style={{ fontSize: "16px", fontWeight: 700, color: (r.risk_score || 0) >= 70 ? "#EF4444" : "rgba(255,255,255,0.9)", fontFamily: "Chakra Petch" }}>{typeof r.risk_score === "number" ? r.risk_score.toFixed(1) : "—"}</div>
                        </div>
                        <div style={{ background: "rgba(255,255,255,0.02)", padding: "8px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.05)" }}>
                          <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.5)", fontFamily: "JetBrains Mono" }}>{kn ? "ಹಿಂದಿನ ಪ್ರಕರಣಗಳು" : "prior firs"}</div>
                          <div style={{ fontSize: "16px", fontWeight: 700, color: "rgba(255,255,255,0.9)", fontFamily: "Chakra Petch" }}>{r.prior_count ?? 0}</div>
                        </div>
                        <div style={{ background: "rgba(255,255,255,0.02)", padding: "8px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.05)" }}>
                          <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.5)", fontFamily: "JetBrains Mono" }}>{kn ? "ಪ್ರಾಥಮಿಕ ವಲಯ" : "jurisdiction"}</div>
                          <div style={{ fontSize: "13px", fontWeight: 500, color: "rgba(255,255,255,0.9)" }}>{r.address_zone || r.zone || "—"}</div>
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", paddingTop: "4px" }}>
                        <button
                          type="button"
                          onClick={() => router.push(`/antarBrain?suspect=${r.suspect_id}`)}
                          style={{
                            padding: "6px 12px",
                            borderRadius: "6px",
                            background: "rgba(255,255,255,0.06)",
                            color: "rgba(255,255,255,0.9)",
                            fontSize: "11px",
                            fontWeight: 600,
                            fontFamily: "Chakra Petch",
                            border: "1px solid rgba(255,255,255,0.15)",
                            cursor: "pointer",
                            transition: "background 0.2s"
                          }}
                          onMouseOver={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.12)"}
                          onMouseOut={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.06)"}
                        >
                          {kn ? "3d ಮೆದುಳಿನಲ್ಲಿ ನೋಡಿ →" : "open in 3d brain →"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT: profile detail */}
        <div className="sx-detailpanel">
          {!selectedId && <div className="sx-detail-empty">{kn ? "ವಿವರಗಳಿಗಾಗಿ ಪ್ರೊಫೈಲ್ ಆಯ್ಕೆಮಾಡಿ" : "Select a profile to view full details"}</div>}
          {selectedId && loadingProfile && !p && <div className="sx-detail-empty"><div className="signal-pulse" style={{ width: 180 }} /></div>}
          {selectedId && p && (
            <div className="sx-dp-inner fade-rise">
              {/* HERO */}
              <div className={`sx-hero r-${tierCls(p.risk_score || 0)}`}>
                <div className="sx-hero-av">{initials(p.full_name)}</div>
                <div className="sx-hero-info">
                  <div className="nm">{p.full_name}</div>
                  <div className="al">
                    {[p.alias && (kn ? `ಅಡ್ಡಹೆಸರು "${p.alias}"` : `alias "${p.alias}"`),
                      p.gender === "M" ? (kn ? "ಪುರುಷ" : "male") : p.gender === "F" ? (kn ? "ಮಹಿಳೆ" : "female") : null,
                      p.age && `${p.age} ${kn ? "ವರ್ಷ" : "yrs"}`,
                      rec?.zone].filter(Boolean).join(" · ")}
                  </div>
                  <div className="badges">
                    <span className="b verified"> {kn ? "ಪರಿಶೀಲಿತ ದಾಖಲೆ" : "VERIFIED RECORD"}</span>
                    <span className={`b r-${tierCls(p.risk_score || 0)}`}>{tier(p.risk_score || 0)} {kn ? "ಅಪಾಯ" : "RISK"}</span>
                    <span className="b id">{p.suspect_id}</span>
                    {rec?.priors != null && <span className="b priors">{rec.priors} {kn ? "ಮೊದಲಿನ" : "priors"}</span>}
                    {rec?.status && <span className="b status">{rec.status}</span>}
                  </div>
                </div>
                <div className="sx-hero-risk">
                  <div className="num">{typeof p.risk_score === "number" ? p.risk_score.toFixed(1) : "—"}</div>
                  <div className="lbl">{kn ? "ಅಪಾಯ ಸೂಚ್ಯಂಕ" : "RISK INDEX"}</div>
                  <div className="bar"><div className="f" style={{ width: `${p.risk_score || 0}%` }} /></div>
                </div>
              </div>

              
              <div className="sx-profile-tabs" style={{ display: "flex", gap: "16px", padding: "16px 24px 0", borderBottom: "1px solid rgba(255,255,255,0.05)", marginBottom: "16px" }}>
                <button onClick={() => setProfileTab("details")} style={{ background: "none", border: "none", color: profileTab === "details" ? "#fff" : "rgba(255,255,255,0.5)", fontWeight: 700, paddingBottom: "12px", borderBottom: profileTab === "details" ? "2px solid #fff" : "2px solid transparent", cursor: "pointer", fontFamily: "Chakra Petch" }}>DETAILS</button>
                <button onClick={() => setProfileTab("osint")} style={{ background: "none", border: "none", color: profileTab === "osint" ? "var(--osint)" : "rgba(255,255,255,0.5)", fontWeight: 700, paddingBottom: "12px", borderBottom: profileTab === "osint" ? "2px solid var(--osint)" : "2px solid transparent", cursor: "pointer", fontFamily: "Chakra Petch" }}>OSINT (Web Recon)</button>
              </div>
              
              {profileTab === "osint" && !osintAllowed && (
                 <div style={{ padding: "24px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontSize: "14px" }}>
                   <div style={{ marginBottom: "12px", color: "var(--osint)" }}>
                     <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                   </div>
                   OSINT is available to administrators.<br/>Log in with an admin ID (A-...) to enable.
                 </div>
              )}
              {profileTab === "osint" && osintAllowed && osintConsentOpen && (
                <div style={{ padding: "24px" }}>
                  <div style={{ border: "1px solid rgba(239, 68, 68, 0.4)", background: "rgba(239, 68, 68, 0.1)", borderRadius: "8px", padding: "16px", textAlign: "left" }}>
                    <div style={{ color: "#EF4444", fontWeight: 700, marginBottom: "8px", fontFamily: "Chakra Petch" }}>OSINT ACCESS CONSENT</div>
                    <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.7)", lineHeight: 1.5 }}>
                      You are about to access the open-source intelligence (OSINT) module. This tool queries public data, social media, and unverified third-party sources.
                      By proceeding, you acknowledge that OSINT data is unverified and all queries are audit-logged.
                    </p>
                    <div style={{ marginTop: "16px", display: "flex", gap: "10px" }}>
                      <button onClick={() => setProfileTab("details")} style={{ padding: "8px 16px", borderRadius: "6px", background: "rgba(255,255,255,0.05)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer", fontSize: "12px", fontWeight: 700 }}>Cancel</button>
                      <button onClick={() => setOsintConsentOpen(false)} style={{ padding: "8px 16px", borderRadius: "6px", background: "#EF4444", color: "#fff", border: "none", cursor: "pointer", fontSize: "12px", fontWeight: 700 }}>I Agree · Enable OSINT</button>
                    </div>
                  </div>
                </div>
              )}
              {profileTab === "osint" && osintAllowed && !osintConsentOpen && (
                <div style={{ padding: "0 24px 24px" }}>
<div className="sx-osint-main" style={{ display: "flex", flexDirection: "column", height: "auto" }}>
          {/* LEFT: query builder */}
          <div className="sx-qbuilder">
            <div className="sx-ql"><span className="req" />{kn ? "ಗುರುತಿನ ಸಿಗ್ನಲ್‌ಗಳು" : "Identity signals"}</div>
            <div style={{ position: "relative", display: "flex", alignItems: "center", gap: "6px" }}>
              <input className="sx-qfield" style={{ flex: 1, paddingRight: "64px" }} value={query} onChange={(e) => setQuery(e.target.value)} placeholder={kn ? "ಪೂರ್ಣ ಹೆಸರು ಅಥವಾ ಅಡ್ಡಹೆಸರು…" : "Full name, alias, phone, plate…"} onKeyDown={(e) => { if (e.key === "Enter") runOsint(); }} />
              <div style={{ position: "absolute", right: "10px", display: "flex", alignItems: "center", gap: "4px" }}>
                <button type="button" onClick={toggleVoice} title={recording ? "Stop listening" : "Speak to search"} style={{ width: 26, height: 26, borderRadius: "50%", border: "none", background: recording ? "rgba(239,68,68,0.2)" : "rgba(255,255,255,0.08)", color: recording ? "#EF4444" : "#22E6F0", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                  {recording ? <MicOff size={13} /> : <Mic size={13} />}
                </button>
                {query && (
                  <button type="button" onClick={() => setQuery("")} title="Clear input" style={{ width: 24, height: 24, borderRadius: "50%", border: "none", background: "rgba(255,255,255,0.08)", color: "#94A3B8", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                    <X size={13} />
                  </button>
                )}
              </div>
            </div>

            <div className="sx-ql">{kn ? "ಗುಪ್ತಚರ ಮೂಲಗಳು" : "Intelligence sources"}</div>
            <div className="sx-src-grid">
              {[["Public Records", "#22E6F0"], ["Social Media", "#FF8C42"], ["Court Records", "#18D69A"], ["News Archives", "#FFB020"], ["Marketplace", "#B026FF"], ["Geo-tagged", "#7A8BA0"]].map(([n, c], i) => (
                <div key={n} className={`sx-src ${i < 5 ? "on" : ""}`}>
                  <span className="dot" style={{ background: c }} />
                  <span className="nm">{n}</span>
                  <span className="cb">{i < 5 ? "" : ""}</span>
                </div>
              ))}
            </div>

            <div className="sx-ql">{kn ? "ಹುಡುಕಾಟ ಆಳ" : "Search depth"}</div>
            <div className="sx-depth">
              {["Surface", "Standard", "Deep", "Full"].map((d, i) => <button key={d} className={i === 1 ? "on" : ""}>{d}</button>)}
            </div>

            <button className="sx-run" onClick={runOsint} disabled={osintLoading}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
              {osintLoading ? (kn ? "ಸ್ಕ್ಯಾನ್…" : "Scanning…") : (kn ? "OSINT ಹುಡುಕಾಟ ಚಲಾಯಿಸಿ" : "Run OSINT search")}
            </button>

            <div className="sx-legal"><b>{kn ? "ಕಾನೂನು ಸೂಚನೆ:" : "Legal Notice:"}</b> {kn ? "ಎಲ್ಲಾ OSINT ಡೇಟಾ ಮುಕ್ತ-ಮೂಲ ಮತ್ತು ಪರಿಶೀಲಿಸದ. ಫಲಿತಾಂಶಗಳನ್ನು ಎಂದಿಗೂ ದೃಢೀಕೃತ ಸತ್ಯವೆಂದು ಪರಿಗಣಿಸಬೇಡಿ." : "All OSINT data is open-source and unverified. Results must never be treated as confirmed facts. This session is audit-logged (KSP Policy §4.2)."}</div>

            <div className="sx-audit">
              <div className="t">{kn ? "ಸೆಶನ್ ಲೆಕ್ಕಪರಿಶೋಧನೆ" : "Session audit log"}</div>
              <div className="row"><span className="ts">00:00</span> {kn ? "ಸೆಶನ್ ಪ್ರಾರಂಭ · DCP Kumar" : "Session initiated · DCP Kumar"}</div>
              {osint && <div className="row"><span className="ts">00:03</span> {kn ? "ಪ್ರಶ್ನೆ ಸಲ್ಲಿಸಲಾಗಿದೆ · " : "Query submitted · "}"{osint.q}"</div>}
              {osint && <div className="row"><span className="ts">00:04</span> {osint.claims.length} {kn ? "ಮುಕ್ತ-ವೆಬ್ ಸಿಗ್ನಲ್‌ಗಳು" : "open-web signals surfaced"}</div>}
            </div>
          </div>

          {/* RIGHT: results */}
          {/* RIGHT: results */}
          <div className="sx-osint-results">
            <div className="sx-rmeta">
              <div>
                <span className="cnt">{osint ? osint.claims.length : (kn ? "—" : "0")} {kn ? "ಮುಕ್ತ-ವೆಬ್ ಸಿಗ್ನಲ್‌ಗಳು" : "open-web signals"}</span>
                {osint && <span className="sub"> {kn ? "ಇದಕ್ಕಾಗಿ" : "for"} "{osint.q}"</span>}
              </div>
              {osintLoading && <span className="scan"><span className="d" /> {kn ? "ಸ್ಕ್ಯಾನ್ ಆಗುತ್ತಿದೆ" : "scanning"}</span>}
            </div>

            {/* Verified anchor from internal DB */}
            {anchor && (
              <div className="sx-anchor">
                <div className={`sx-anchor-av r-${tierCls(anchor.risk_score || 0)}`}>{initials(anchor.full_name)}</div>
                <div className="sx-anchor-body">
                  <div className="nm">{anchor.full_name} <span className="vtag"> {kn ? "FIR-ಲಿಂಕ್" : "FIR-Linked"} {anchor.suspect_id}</span></div>
                  <div className="sub">{anchor.alias ? `alias "${anchor.alias}" · ` : ""}{anchor.address_zone} · {anchor.prior_count} {kn ? "ಮೊದಲಿನ" : "priors"} · {kn ? "ಅಪಾಯ" : "risk"} {anchor.risk_score ?? "—"}</div>
                </div>
                <button className="sx-anchor-btn" onClick={() => router.push(`/antarBrain?suspect=${anchor.suspect_id}`)}>{kn ? "ಮೆದುಳಿನಲ್ಲಿ →" : "Show in Brain →"}</button>
              </div>
            )}

            {/* 4-TAB MULTI-MODULE RECON WORKBENCH (Layer 5) */}
            {reconData && (
              <div className="sx-recon-workbench" style={{ margin: "16px 0", border: "1px solid rgba(255,140,66,0.3)", borderRadius: "10px", background: "rgba(10,14,23,0.85)", overflow: "hidden" }}>
                <div className="sx-recon-tabs" style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.4)" }}>
                  {[
                    ["maltego", "Maltego Graph"],
                    ["telecom", "PhoneInfoga"],
                    ["sherlock", "Sherlock Handles"],
                    ["bbot", "BBOT Scan Tree"],
                  ].map(([k, label]) => (
                    <button
                      key={k}
                      onClick={() => setReconTab(k)}
                      style={{
                        flex: 1,
                        padding: "10px 8px",
                        fontSize: "12px",
                        fontWeight: reconTab === k ? "700" : "500",
                        color: reconTab === k ? "#FF8C42" : "#94A3B8",
                        background: reconTab === k ? "rgba(255,140,66,0.12)" : "transparent",
                        borderBottom: reconTab === k ? "2px solid #FF8C42" : "none",
                        cursor: "pointer",
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className="sx-recon-body" style={{ padding: "14px", maxHeight: "320px", overflowY: "auto" }}>
                  {reconTab === "maltego" && (
                    <div>
                      <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.8)", marginBottom: "8px", fontWeight: 600 }}>
                        maltego linkage topology · {reconData.maltego_linkage?.nodes?.length || 0} nodes · {reconData.maltego_linkage?.edges?.length || 0} edges
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                        {(reconData.maltego_linkage?.nodes || []).map((n, idx) => (
                          <div key={n?.id || idx} style={{ padding: "6px 10px", borderRadius: "6px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", fontSize: "12px", color: "rgba(255,255,255,0.9)" }}>
                            <span style={{ fontWeight: 600, color: "rgba(255,255,255,0.6)" }}>{String(n?.type || n?.node_type || "NODE").toLowerCase()}:</span> {n?.label || n?.name || n?.id || "—"}
                            {n?.verified ? <span style={{ marginLeft: "6px", fontSize: "10px", color: "rgba(255,255,255,0.5)" }}>● verified</span> : <span style={{ marginLeft: "6px", fontSize: "10px", color: "rgba(255,255,255,0.3)" }}>○ unverified</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {reconTab === "telecom" && (
                    <div>
                      <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.8)", marginBottom: "8px", fontWeight: 600 }}>
                        phoneinfoga telecom footprint · e.164 geo-footprinting
                      </div>
                      <div style={{ fontSize: "13px", color: "#E2E8F0" }}>
                        <div><b>Number / Query:</b> {reconData.phone_infoga?.phone_query || "N/A"}</div>
                        <div><b>Line Classification:</b> {reconData.phone_infoga?.line_type || "Unknown"} ({reconData.phone_infoga?.country || "IN"})</div>
                        <div style={{ marginTop: "8px", color: "#94A3B8" }}>
                          <b>Co-occurring Internal Records:</b> {(reconData.phone_infoga?.co_occurring_records || []).join(", ") || "None"}
                        </div>
                      </div>
                    </div>
                  )}

                  {reconTab === "sherlock" && (
                    <div>
                      <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.8)", marginBottom: "8px", fontWeight: 600 }}>
                        sherlock digital profiles · strict unverified quarantine
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {(reconData.sherlock_handles || []).map((h, i) => (
                          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", background: "rgba(255,255,255,0.04)", borderRadius: "6px", fontSize: "12px" }}>
                            <div>
                              <span style={{ fontWeight: 700, color: "#E2E8F0" }}>{h?.platform || "Platform"}</span> · <span style={{ color: "#94A3B8" }}>@{h?.handle || "handle"}</span>
                            </div>
                            <span style={{ padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700, background: "rgba(255,140,66,0.2)", color: "#FF8C42" }}>
                              {h?.badge || "FOUND"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {reconTab === "bbot" && (
                    <div>
                      <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.8)", marginBottom: "8px", fontWeight: 600 }}>
                        bbot event scan tree · chronological recon audit
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px", fontFamily: "monospace" }}>
                        {(reconData.bbot_scan_tree || []).map((e, idx) => (
                          <div key={e?.id || idx} style={{ padding: "6px", background: "rgba(0,0,0,0.3)", borderLeft: "2px solid #18D69A" }}>
                            <span style={{ color: "#18D69A", fontWeight: 700 }}>[{String(e?.event_type || "SCAN").toUpperCase()}]</span> <span style={{ color: "#94A3B8" }}>{e?.detail || "—"}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {!osint && !osintLoading && (
              <div className="sx-osint-empty">
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--osint)" strokeWidth="1.4"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
                <p>{kn ? "ಮುಕ್ತ-ಮೂಲ ಸಿಗ್ನಲ್‌ಗಳಿಗಾಗಿ ಪ್ರಶ್ನೆ ನಮೂದಿಸಿ ಮತ್ತು “OSINT ಹುಡುಕಾಟ ಚಲಾಯಿಸಿ” ಒತ್ತಿ." : "Enter a query and run an OSINT search to surface open-web signals alongside the verified record."}</p>
              </div>
            )}

            {osint && osint.claims.length === 0 && !osintLoading && (
              <div className="sx-osint-empty"><p>{kn ? "ಯಾವುದೇ ಮುಕ್ತ-ವೆಬ್ ಸಿಗ್ನಲ್‌ಗಳು ಕಂಡುಬಂದಿಲ್ಲ." : "No open-web signals found for this query."}</p></div>
            )}

            {osint?.claims.map((c, i) => {
              const pct = Math.round((c.confidence || 0) * 100);
              return (
                <div className="sx-claim" key={i}>
                  <div className="sx-claim-hd">
                    <span className="src">OSINT</span>
                    <span className={`status ${c.status}`}>{c.status || "unverified"}</span>
                    <span className="conf">{pct}%</span>
                  </div>
                  <div className="sx-claim-body">{c.claim}</div>
                  <div className="sx-claim-ft">
                    <div className="bar"><div className="f" style={{ width: `${pct}%` }} /></div>
                    {/* a link from the open web: only an http(s) address is ever made clickable */}
                    {/^https?:\/\//i.test(c.source_url || "") && <a href={c.source_url} target="_blank" rel="noopener noreferrer nofollow">source ↗</a>}
                    <span className="warn">{kn ? "ಪರಿಶೀಲಿಸದ · ಮುಕ್ತ-ಮೂಲ" : "Unverified · open-source"}</span>
                  </div>
                </div>
              );
            })}

            {/* AI correlation from Second Brain */}
            {profile?.similar_cases?.[0] && osint && (
              <div className="sx-infer">
                <span className="ico"></span>
                <div>
                  <div className="t">{kn ? "AI ಸಂಬಂಧ ಸಲಹೆ" : "AI Correlation Suggestion"}</div>
                  <div className="s">{profile.similar_cases[0].summary?.slice(0, 220)}… <span className="c">{kn ? "ವಿಶ್ವಾಸ" : "Confidence"}: {Math.round((profile.similar_cases[0].score || 0) * 100)}% · {kn ? "ಊಹಿತ ಮಾತ್ರ" : "inferred only"}</span></div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    )}
              
              {profileTab === "details" && rec && (
              <div className="sx-sections sx-casefile">
                {/* Key figures - four numbers an officer reads first */}
                <div className="sx-kpis sx-sec-full">
                  <div><b>{rec.linkedCases ?? "—"}</b><span>{kn ? "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು" : "linked cases"}</span></div>
                  <div><b className={rec.lastFirDays != null && rec.lastFirDays <= 30 ? "warn" : ""}>{rec.lastFirDays != null ? `${rec.lastFirDays}d` : "—"}</b><span>{kn ? "ಕೊನೆಯ FIR ನಿಂದ" : "since last FIR"}</span></div>
                  <div><b>{p.associates?.length ?? 0}</b><span>{kn ? "ಸಹಚರರು" : "associates"}</span></div>
                  <div><b>{rec.priors ?? "—"}</b><span>{kn ? "ಮೊದಲಿನ ಪ್ರಕರಣಗಳು" : "prior counts"}</span></div>
                </div>

                {/* Why this risk score - points each factor actually contributed */}
                {(p.risk_attributions || p.factors) && (
                  <div className="sx-sec sx-sec-full">
                    <div className="sx-sec-t">{kn ? "ಈ ಅಪಾಯ ಅಂಕ ಏಕೆ" : "Why this risk score"} <span className="cnt">{kn ? "4-ಅಂಶ ಮಾದರಿ" : "4-factor model · points"}</span></div>
                    <p className="sx-why">
                      {(() => {
                        const drivers = rec.contrib.filter((c) => c.pts > 0).sort((a, b) => b.pts - a.pts);
                        const idle = rec.contrib.filter((c) => c.pts === 0);
                        if (kn) return `${Math.round(p.risk_score || 0)}/100 - ${drivers.map((d) => d.label).join(", ") || "ಯಾವುದೇ ಪ್ರಮುಖ ಅಂಶವಿಲ್ಲ"}.`;
                        return (<>
                          Scored <b>{Math.round(p.risk_score || 0)}/100</b>
                          {drivers.length ? <> driven by {drivers.map((d, i) => <span key={d.k}>{i > 0 && (i === drivers.length - 1 ? " and " : ", ")}<b>{d.label.toLowerCase()}</b>{d.detail ? ` (${d.detail})` : ""}</span>)}</> : " with no strong driver"}.
                          {idle.length > 0 && <> No contribution from {idle.map((d) => d.label.toLowerCase()).join(" or ")}.</>}
                        </>);
                      })()}
                    </p>
                    <div className="sx-contrib">
                      {rec.contrib.map((c) => (
                        <div key={c.k} className={c.pts ? "" : "zero"}>
                          <span className="lbl">{c.label}</span>
                          <span className="trk"><i style={{ width: `${Math.min(100, (c.pts / 30) * 100)}%` }} /></span>
                          <span className="pts">{c.pts ? `+${c.pts}` : "0"}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Record - only fields that exist in the data */}
                <div className="sx-sec">
                  <div className="sx-sec-t">{kn ? "ದಾಖಲೆ" : "Record"}</div>
                  <div className="sx-field"><span className="k">{kn ? "ಐಡಿ" : "FIR-linked ID"}</span><span className="v mono">{p.suspect_id}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಹೆಸರು" : "Name"}</span><span className="v">{p.full_name}</span></div>
                  {p.alias && <div className="sx-field"><span className="k">{kn ? "ಅಡ್ಡಹೆಸರು" : "Alias"}</span><span className="v">{p.alias}</span></div>}
                  {rec.zone && <div className="sx-field"><span className="k">{kn ? "ಪ್ರಾಥಮಿಕ ವಲಯ" : "Primary zone"}</span><span className="v">{rec.zone}</span></div>}
                  {rec.status && <div className="sx-field"><span className="k">{kn ? "ಸ್ಥಿತಿ" : "Status"}</span><span className="v red">{rec.status}</span></div>}
                  {(p.age || p.gender) && <div className="sx-field"><span className="k">{kn ? "ಲಿಂಗ · ವಯಸ್ಸು" : "Gender · age"}</span><span className="v">{[cap(p.gender), p.age].filter(Boolean).join(" · ")}</span></div>}
                </div>

                {/* Recommended next steps */}
                <div className="sx-sec">
                  <div className="sx-sec-t">{kn ? "ಮುಂದಿನ ಹೆಜ್ಜೆಗಳು" : "Recommended next steps"}</div>
                  {p.leads?.length ? (
                    <ol className="sx-leads">{p.leads.slice(0, 4).map((l, i) => <li key={i}>{l}</li>)}</ol>
                  ) : (
                    <div className="sx-empty-sm">{kn ? "ಯಾವುದೇ ಸೂಚಿತ ಕ್ರಮವಿಲ್ಲ" : "No suggested actions for this record."}</div>
                  )}
                </div>

                {/* Modus operandi */}
                {rec.moText && (
                  <div className="sx-sec sx-sec-full">
                    <div className="sx-sec-t">{kn ? "ಕಾರ್ಯ ವಿಧಾನ (MO)" : "Modus operandi"}</div>
                    <div className="sx-mo">{rec.moText}</div>
                  </div>
                )}

                {/* Known associates - opens their record in place */}
                <div className="sx-sec sx-sec-full">
                  <div className="sx-sec-t">{kn ? "ತಿಳಿದ ಸಹಚರರು" : "Known associates"} <span className="cnt">{p.associates?.length || 0}</span></div>
                  {(!p.associates || p.associates.length === 0) && <div className="sx-empty-sm">{kn ? "ಯಾವುದೇ ಲಿಂಕ್ ಇಲ್ಲ" : "No recorded associates in FIR data."}</div>}
                  <div className="sx-assoc-list sx-assoc-grid">
                    {(p.associates || []).slice(0, 6).map((a) => (
                      <button key={a.id} className="sx-assoc" onClick={() => { setProfileTab("details"); setSelectedId(a.id); }}
                              title={kn ? "ದಾಖಲೆ ತೆರೆಯಿರಿ" : `Open ${a.name}'s record`}>
                        <span className={`av r-${tierCls(a.risk || 0)}`}>{initials(a.name)}</span>
                        <span className="ab"><span className="an">{a.name}</span><span className="as">{a.id}</span></span>
                        <span className="lk">{a.reason}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Cross-case matches - only ones strong enough to be worth reading */}
                {rec.strongMatches.length > 0 && (
                  <div className="sx-sec sx-sec-full">
                    <div className="sx-sec-t">{kn ? "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು" : "Similar past cases"} <span className="cnt">{kn ? "ಊಹಿತ" : "inferred · ≥25% match"}</span></div>
                    {rec.strongMatches.slice(0, 3).map((c, i) => (
                      <div key={i} className="sx-linkcase">
                        <span className="score">{Math.round((c.score || 0) * 100)}%</span>
                        <span className="txt">{(c.summary || "").slice(0, 200)}{(c.summary || "").length > 200 ? "…" : ""}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              )}
              {/* Actions */}
              <div className="sx-actions">
                {/* Watchlisting a person is a real-world effect: this files a request that a
                    supervising officer must approve (app/core/hitl.py). Approvers review
                    requests; they do not file them. */}
                {role !== "Approver" && (
                  <button className="sx-act hitl-request" onClick={() => setWatchRequest(true)}
                          title={kn ? "ಮೇಲ್ವಿಚಾರಕರ ಅನುಮೋದನೆ ಅಗತ್ಯ" : "Requires supervising officer approval"}>
                    <ShieldCheck size={13} aria-hidden="true" /> {kn ? "ವೀಕ್ಷಣಾ ಪಟ್ಟಿ ವಿನಂತಿ" : "Request watchlist"}
                  </button>
                )}
                <button className="sx-act" onClick={() => router.push(`/map?zone=${encodeURIComponent(p.address_zone || p.zone || "")}`)}>{kn ? "ನಕ್ಷೆಯಲ್ಲಿ" : "View on Map"}</button>
                <button className="sx-act" onClick={() => router.push(`/antar?q=${encodeURIComponent("Tell me about " + (p.full_name || ""))}`)}>{kn ? "Antar ಕೇಳಿ" : "Ask Antar"}</button>
                <button className="sx-act primary" onClick={() => router.push(`/antarBrain?suspect=${p.suspect_id}`)}>{kn ? "ಮೆದುಳಿನಲ್ಲಿ →" : "Show in Brain →"}</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="sx-page" />}>
      <SearchContent />
    </Suspense>
  );
}


