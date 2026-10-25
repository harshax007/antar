"use client";

import { useCallback, useEffect, useMemo, useRef, useState, Suspense } from "react";
import OsintReport, { reportText as osintReportText } from "@/components/OsintReport";
import OsintDocs from "@/components/OsintDocs";
import { fetchAPI } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useLang } from "@/components/Providers";
import { Mic, MicOff, X, ShieldCheck, Search, ArrowRight, Brain, MapPin, Sparkles, FolderGit2, Calendar, Users, Hash, Activity } from "lucide-react";
import ProposeAction from "@/components/ProposeAction";
import { AnimatePresence, motion } from "framer-motion";
import { SPRING } from "@/components/ui/MaterialPanel";
import "@/components/editorial-search.css";
import BrainLoader, { OSINT_STEPS, OSINT_ORBS } from "@/components/BrainLoader";

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
  const parts = String(name).split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
  return (
    <>
      {parts.map((p, i) =>
        p.toLowerCase() === query.toLowerCase() ? (
          <span key={i} className="sx-hl">{p}</span>
        ) : (
          p
        )
      )}
    </>
  );
}


// Explain WHY a result matched - officers should never have to guess.
function matchWhy(r) {
  const field = { full_name: 'name', alias: 'alias', father_name: 'father', phone_hash: 'phone' }[r.match_field] || r.match_field;
  switch (r.match_method) {
    case 'exact': return { cls: 'ex', txt: `exact on ${field}` };
    case 'phone_exact': return { cls: 'ex', txt: `exact on phone` };
    case 'jaro_winkler': return { cls: 'fz', txt: `typo on ${field}` };
    case 'soundex': return { cls: 'ph', txt: `phonetic on ${field}` };
    case 'id_exact': return { cls: 'ex', txt: 'exact on ID' };
    default: return null;
  }
}
// The profile sends 99999 days when no FIR for the person carries a usable date. That is
// "not on record", not a number to print ("99999d").
const recencyDays = (d) => (d == null || !Number.isFinite(Number(d)) || Number(d) >= 9999 ? null : Number(d));
function sinceText(d, kn, short = false) {
  if (d == null) return kn ? "ದಾಖಲೆಯಲ್ಲಿಲ್ಲ" : "Not on record";
  if (d < 1) return kn ? "ಇಂದು" : "Today";
  if (d < 60) return kn ? `${d} ದಿನ` : (short ? `${d} days` : `${d} days ago`);
  if (d < 730) { const m = Math.round(d / 30); return kn ? `${m} ತಿಂಗಳು` : (short ? `${m} months` : `${m} months ago`); }
  const y = Math.round(d / 365); return kn ? `${y} ವರ್ಷ` : (short ? `${y} years` : `${y} years ago`);
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
  const view = ["money", "social"].includes(sp?.get("view")) ? sp.get("view") : "people";
  const setView = (v) => router.replace(v === "people" ? "/search" : `/search?view=${v}`);

  const [role, setRoleState] = useState("Officer");
  const [trueAdmin, setTrueAdmin] = useState(false);
  const [showOsintInfo, setShowOsintInfo] = useState(false);
  const [profileTab, setProfileTab] = useState("details");
  const [osintConsentOpen, setOsintConsentOpen] = useState(true);
  const [osintAbout, setOsintAbout] = useState(false);   // "Know more": what OSINT checks, opened from the consent card // consent gate before OSINT is ever enabled
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

  // Standalone OSINT Workbench State (Strictly isolated from FIR search & Antar core)
  const [osintQuery, setOsintQuery] = useState("");
  const [osint, setOsint] = useState(null);
  const [osintLoading, setOsintLoading] = useState(false);
  const [reconData, setReconData] = useState(null);
  const [reconTab, setReconTab] = useState("decoder"); // "decoder" | "maltego" | "telecom" | "sherlock" | "bbot" | "bnss94"
  const [osintSources, setOsintSources] = useState([]);   // [] = every kind of page; a chip narrows it
  const [osintDepth, setOsintDepth] = useState("standard");
  const [osintAuditLog, setOsintAuditLog] = useState([]);
  const [osintRecording, setOsintRecording] = useState(false);
  const osintRecRef = useRef(null);

  const getSessionOfficer = useCallback(() => {
    try {
      const s = JSON.parse(sessionStorage.getItem("antar_session") || "null");
      if (s?.officer || s?.name || s?.username) {
        return `${s.role || role || "Inspector"} · ${s.officer || s.name || s.username}`;
      }
      if (s?.role) return `${s.role} Session`;
    } catch {}
    return `${role || "Inspector"} Session`;
  }, [role]);

  const appendOsintAudit = useCallback((eventText) => {
    const now = new Date();
    const ts = now.toTimeString().slice(0, 8);
    setOsintAuditLog((prev) => [...prev.slice(-9), { ts, text: eventText }]);
  }, []);

  const toggleOsintSource = useCallback((srcKey) => {
    setOsintSources((prev) => {
      if (prev.includes(srcKey)) return prev.filter((k) => k !== srcKey);
      return [...prev, srcKey];
    });
  }, []);

  const toggleOsintVoice = useCallback(() => {
    if (osintRecording && osintRecRef.current) {
      osintRecRef.current.stop();
      setOsintRecording(false);
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
      if (transcript) setOsintQuery((prev) => (prev ? prev + " " + transcript : transcript));
      setOsintRecording(false);
    };
    rec.onerror = () => setOsintRecording(false);
    rec.onend = () => setOsintRecording(false);
    osintRecRef.current = rec;
    rec.start();
    setOsintRecording(true);
  }, [osintRecording, kn]);

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

  // ── Standalone OSINT execution (ONLY runs when user explicitly triggers in OSINT tab; ZERO FIR access) ──
  const runOsint = useCallback((overrideTarget) => {
    const q = (typeof overrideTarget === "string" ? overrideTarget : osintQuery).trim();
    if (!q || q.length < 2) {
      flashToast(kn ? "ಕನಿಷ್ಠ 2 ಅಕ್ಷರಗಳ ಗುರಿಯನ್ನು ನಮೂದಿಸಿ" : "Enter a target identifier (min 2 chars) to run OSINT", "warn");
      return;
    }
    if (typeof overrideTarget === "string") {
      setOsintQuery(overrideTarget);
    }
    const srcParam = osintSources.length ? `&sources=${encodeURIComponent(osintSources.join(","))}` : "";
    const depthParam = `&depth=${encodeURIComponent(osintDepth)}`;
    setOsintLoading(true);
    appendOsintAudit(`Submitted standalone OSINT query "${q}" [depth=${osintDepth.toUpperCase()}]`);
    fetchAPI(`/api/osint/investigate?entity=${encodeURIComponent(q)}${srcParam}${depthParam}&lang=${kn ? "kn" : "en"}`)
      .then((r) => [r?.web || { claims: [], reached: false }, r])
      .catch(() => Promise.all([
        fetchAPI(`/api/osint/?entity=${encodeURIComponent(q)}${srcParam}${depthParam}`).catch(() => ({ claims: [], reached: false })),
        fetchAPI(`/api/osint/recon?entity=${encodeURIComponent(q)}${srcParam}${depthParam}`).catch(() => null),
      ]))
      .then(([d, r]) => {
        const claimList = d?.claims || [];
        setOsint({
          q,
          claims: claimList,
          summary: d?.summary || "",
          risk_flags: d?.risk_flags || [],
          matched_risk_terms: d?.matched_risk_terms || [],
          query_executed: d?.query_executed || q,
          reached: d?.reached !== false,
          isolation_mode: d?.isolation_mode || "STANDALONE_NO_FIR_ACCESS",
        });
        setReconData(r);
        const decodedLabel = r?.forensic_decoder?.target_label || "Identifier";
        appendOsintAudit(
          (kn
            ? `${decodedLabel}: ${d?.pages_checked ?? "?"} ರಲ್ಲಿ ${claimList.length} ಪುಟಗಳು ಉಲ್ಲೇಖಿಸುತ್ತವೆ · ${r?.live_checks?.length || 0} ನೇರ ಪರಿಶೀಲನೆ · ${r?.official_checks?.length || 0} ಅಧಿಕೃತ ಪರಿಶೀಲನೆ`
            : `${decodedLabel}: ${claimList.length} of ${d?.pages_checked ?? "?"} pages mention it · ${r?.live_checks?.length || 0} live checks · ${r?.official_checks?.length || 0} official checks`)
        );
      })
      .finally(() => setOsintLoading(false));
  }, [osintQuery, osintSources, osintDepth, appendOsintAudit, flashToast, kn]);

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
    lastFirDays: recencyDays(p.raw_factors?.recency_days),
    status: cap(p.arrest_status) || (p.mo_summary || "").match(/arrest status ([\w_]+)/i)?.[1]?.replace(/_/g, " ") || null,
    moText: (p.mo_summary || "").replace(/\s*Prior count \d+;\s*arrest status [\w_]+\.?/i, "").trim(),
    contrib: [
      // No count here on purpose: profile_agent's risk model and its MO summary use two
      // different case-linkage lookups (e.g. 46 vs 69 for S0041). Showing both numbers on
      // one screen reads as an error, so the key figures carry the MO count only.
      ["frequency", kn ? "ಆಗಾಗ್ಗೆ ಅಪರಾಧ" : "Frequent offending", null],
      ["recency", kn ? "ಇತ್ತೀಚಿನ ಚಟುವಟಿಕೆ" : "Recent activity", recencyDays(p.raw_factors?.recency_days) != null ? (kn ? `${sinceText(recencyDays(p.raw_factors.recency_days), kn)} ಹಿಂದೆ` : `last FIR ${sinceText(recencyDays(p.raw_factors.recency_days), kn)}`) : (kn ? "ದಿನಾಂಕವಿರುವ FIR ಇಲ್ಲ" : "no dated FIR on record")],
      ["severity", kn ? "ಗಂಭೀರ ಅಪರಾಧಗಳು" : "Serious offences", null],
      ["centrality", kn ? "ಇತರರೊಂದಿಗೆ ಸಂಪರ್ಕ" : "Links to others", null],
    ].map(([k, label, detail]) => ({ k, label, detail, pts: Math.round(p.risk_attributions?.[k] ?? (p.factors?.[k] || 0) * 25) })),
    strongMatches: (p.similar_cases || []).filter((c) => (c.score || 0) >= 0.25),
  } : null;
  // Search has three views: People (records), the Money trail (/search?view=money) and
  // Social insights (/search?view=social)
  if (view === "money" || view === "social") {
    return (
      <div className={`sx-page sx-page--money sx-page--${view}`}>
        {/* the same four tabs, in the same place, as the People view */}
        <SearchViews view={view} onChange={setView} kn={kn}
          osint={osintAllowed ? { on: false, toggle: () => { setProfileTab("osint"); setView("people"); } } : null} />
        {view === "money" ? <MoneyTrail /> : <SocialInsights />}
      </div>
    );
  }

  return (
    <div className="sx-page">
      {p && (
        <ProposeAction open={watchRequest} onClose={() => setWatchRequest(false)} type="watchlist_add" kn={kn}
          defaults={{ watch_type: "entity", target: p.suspect_id, label: `Watch · ${p.full_name} (${p.suspect_id})` }}
          evidence={[
            { label: kn ? "ಅಪಾಯ ಅಂಕ" : "Risk score", value: `${Math.round(p.risk_score || 0)}/100` },
            rec?.linkedCases != null && { label: kn ? "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು" : "Linked cases", value: String(rec.linkedCases) },
            rec?.lastFirDays != null && { label: kn ? "ಕೊನೆಯ FIR" : "Last FIR", value: sinceText(rec.lastFirDays, kn) },
            rec?.status && { label: kn ? "ಸ್ಥಿತಿ" : "Status", value: rec.status },
            (p.associates?.length ?? 0) > 0 && { label: kn ? "ಸಹಚರರು" : "Associates", value: String(p.associates.length) },
          ].filter(Boolean)} />
      )}
      <div className="sx-md">
        {/* LEFT: search + results list */}
        <div className="sx-listpanel">
          <div className="sx-searchwrap">
            <SearchViews view={view} onChange={setView} kn={kn}
              osint={osintAllowed ? { on: profileTab === "osint", toggle: () => setProfileTab(profileTab === "osint" ? "details" : "osint") } : null} />
            <header className="sx-intro">
              <h1>{kn ? <>ಹುಡುಕಾಟ · <em>ಅಪರಾಧ ದಾಖಲೆ</em></> : <>Search · <em>Criminal Record</em></>}</h1>
              <p>{kn
                ? "ಹೆಸರು, ಅಡ್ಡಹೆಸರು, ತಂದೆಯ ಹೆಸರು, ಫೋನ್ ಅಥವಾ ವಾಹನ ಸಂಖ್ಯೆ. ದಾಖಲೆ ತೆರೆಯಿರಿ: ಪ್ರಕರಣಗಳು, ಅಪಾಯ, ಸಹಚರರು."
                : "For station officers and investigators before an arrest or a visit: find a person by name, alias, father's name, phone or vehicle plate, then open their FIRs, risk, associates and money trail."}</p>
            </header>
            <div className="sx-searchbar">
              <Search size={15} />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={kn ? "ಹೆಸರು, ಅಡ್ಡಹೆಸರು, ಫೋನ್, ನಂ.ತಟ್ಟೆ…" : "Search name, alias, phone, vehicle plate…"} aria-label={kn ? "ಶಂಕಿತರನ್ನು ಹುಡುಕಿ" : "Search suspects"} />
              <button type="button" className="clr" onClick={toggleVoice} title={recording ? "Stop listening" : "Speak suspect name"} style={{ background: recording ? "rgba(239,68,68,0.16)" : "transparent", color: recording ? "#F87171" : "#94A3B8", marginRight: query ? "4px" : "0" }}>
                {recording ? <MicOff size={14} /> : <Mic size={14} />}
              </button>
              {query && (
                <button type="button" className="clr" onClick={() => setQuery("")} aria-label="Clear">
                  <X size={14} />
                </button>
              )}
            </div>
            <div className="sx-fchips">
              {FILTERS.map((f) => (
                <button key={f.key} className={filterType === f.key ? "on" : ""} onClick={() => setFilterType(f.key)}>
                  {filterType === f.key && <motion.span layoutId="sx-fchip-pill" className="sx-fchip-pill" transition={SPRING} />}
                  {kn ? f.kn : f.en}
                </button>
              ))}
            </div>
            <div className="sx-enginehint">
              {kn ? "ಕಾಗುಣಿತ ತಪ್ಪಿದ್ದರೂ ಹೆಸರು ಸಿಗುತ್ತದೆ (Yellappa ≈ Yellapa)" : "Matches close spellings and phonetic variants (Yellappa ≈ Yellapa ≈ Ylappa)"}
            </div>
          </div>

          {trackToast && (
            <div role="status" className={`sx-toast ${trackToast.tone || "ok"}`}>
              {trackToast.text}
            </div>
          )}

          {identityHypotheses.length > 0 && (
            <div className="sx-hypbox">
              <div className="sx-hypbox-hd">
                INFERRED CROSS-SOURCE IDENTITY HYPOTHESES · REQUIRES INSPECTOR REVIEW
              </div>
              {identityHypotheses.slice(0, 2).map((h) => (
                <div key={h.hypothesis_id} className="sx-hyprow">
                  <div>
                    <span className="sx-hyp-nm">{h.entity_a.name} ({h.entity_a.id})</span>
                    {" ≈ "}
                    <span className="sx-hyp-nm">{h.entity_b.name} ({h.entity_b.id})</span>
                    <div className="sx-hyp-meta">
                      Confidence: {Math.round(h.confidence * 100)}% · {h.reasons.join(", ")}
                    </div>
                  </div>
                  <div className="sx-hyp-acts">
                    {[["confirm", "Confirm"], ["reject", "Reject"]].map(([action, label]) => (
                      <button key={action} disabled={!canReviewHypotheses}
                        title={canReviewHypotheses ? undefined : (kn ? "ಇನ್ಸ್‌ಪೆಕ್ಟರ್ ಅಥವಾ ಮೇಲಿನ ಶ್ರೇಣಿ ಅಗತ್ಯ" : `Inspector or higher rank required (you are signed in as ${role})`)}
                        onClick={() => handleHypothesisAction(h.hypothesis_id, action)}
                        className={`sx-hyp-btn ${action}`}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="sx-sortrow">
            <span>
              {results
                ? `${results.length} ${kn ? "ಫಲಿತಾಂಶ" : "records"} · ${isSearch ? (kn ? "ಹತ್ತಿರದ ಹೊಂದಾಣಿಕೆ" : "including close spellings") : (kn ? "ಪರಿಶೀಲಿತ ದಾಖಲೆ" : "verified registry")}${isSearch && filterType !== "all" ? ` · ${FILTERS.find((f) => f.key === filterType)?.[kn ? "kn" : "en"]} ${kn ? "ಮಾತ್ರ" : "only"}` : ""}`
                : (kn ? "ಲೋಡ್…" : "loading…")}
            </span>
            <span className="sv">{kn ? "ಅಪಾಯ ↓" : "Sorted by risk ↓"}</span>
          </div>

          <div className="sx-results" role="list">
            {results === null && <div className="sx-listloading"><div className="signal-pulse" style={{ width: 140 }} /></div>}
            {results && results.length === 0 && (
              <div className="sx-nomatch">
                <p>{kn ? "ಯಾವುದೇ ದಾಖಲೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ." : "No matching records found."}</p>
                {unknownDiscovery && (
                  <div className="sx-unknown-box">
                    <div className="sx-unknown-ttl">
                      {kn ? "ಅಜ್ಞಾತ ಲೀಡ್ ಅನ್ವೇಷಣೆ ಪ್ರೋಟೋಕಾಲ್ ಸಕ್ರಿಯ" : "UNKNOWN-FIRST DISCOVERY PROTOCOL ACTIVE"}
                    </div>
                    <div className="sx-unknown-msg">
                      {unknownDiscovery.message}
                    </div>
                    {unknownDiscovery.nearest_neighbors?.length > 0 && (
                      <div className="sx-unknown-nn">
                        <b>Phonetic Nearest Neighbors:</b> {unknownDiscovery.nearest_neighbors.map((n) => `${n.full_name} (${Math.round(n.match_score * 100)}%)`).join(", ")}
                      </div>
                    )}
                    <button
                      onClick={() => trackUnknownLead(query)}
                      className="sx-unknown-btn"
                    >
                      + {kn ? "ಈ ಅಜ್ಞಾತ ಲೀಡ್ ಅನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ" : "Track Unknown Lead in Second Brain"}
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
                <button
                  key={r.suspect_id}
                  id={`sx-row-${r.suspect_id}`}
                  role="listitem"
                  className={`sx-rrow ${selectedId === r.suspect_id ? "active" : ""}`}
                  onClick={() => {
                    setSelectedId(r.suspect_id);
                    // stacked on a phone, the record is below the list: bring it into view
                    if (window.innerWidth <= 900) setTimeout(() => document.querySelector(".sx-detailpanel")?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
                  }}
                >
                  {selectedId === r.suspect_id && <motion.span layoutId="sx-row-sel" className="sx-row-sel" transition={SPRING} />}
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
              );
            })}
          </div>
        </div>

        {/* RIGHT: Standalone OSINT Workbench (when profileTab === "osint") OR FIR Profile Detail (when profileTab === "details") */}
        <div className="sx-detailpanel">
          {profileTab === "osint" && (
            <div className="sx-dp-inner fade-rise">
              <div className="sx-profile-tabs" style={{ marginTop: 0 }}>
                <div className="sx-ptabs-left">
                  <button
                    type="button"
                    className={`sx-ptab ${profileTab === "details" ? "on" : ""}`}
                    onClick={() => setProfileTab("details")}
                  >
                    <Activity size={13} />
                    {profileTab === "details" && <motion.span layoutId="sx-ptab-line" className="sx-ptab-line" transition={SPRING} />}
                    <span>{kn ? "ವಿವರಗಳು ಮತ್ತು ಕೇಸ್‌ಫೈಲ್" : "Details & Casefile"}</span>
                  </button>
                  <button
                    type="button"
                    className={`sx-ptab osint ${profileTab === "osint" ? "on" : ""}`}
                    onClick={() => setProfileTab("osint")}
                  >
                    <Sparkles size={13} />
                    {profileTab === "osint" && <motion.span layoutId="sx-ptab-line" className="sx-ptab-line" transition={SPRING} />}
                    <span>{kn ? "ಸ್ವತಂತ್ರ OSINT ಮತ್ತು ಫಾರೆನ್ಸಿಕ್ಸ್" : "Open-source checks (OSINT)"}</span>
                  </button>
                </div>
                <div className="sx-ptabs-actions">
                  <span
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: "10px",
                      padding: "4px 9px",
                      borderRadius: "6px",
                      background: "rgba(255,255,255,0.05)",
                      border: "1px solid rgba(255,255,255,0.14)",
                      color: "#CBD5E1",
                      letterSpacing: "0.04em",
                    }}
                  >
                    {kn ? "FIR ಸಂಪರ್ಕವಿಲ್ಲ" : "No FIR access"}
                  </span>
                </div>
              </div>

              {!osintAllowed && (
                <div className="sx-osint-locked">
                  <div className="sx-osint-locked-ico">
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                  </div>
                  OSINT is available to authorized investigators.<br />Log in with an Inspector or Admin ID to enable.
                </div>
              )}

              {osintAllowed && osintConsentOpen && (
                <div className="sx-osint-consent-wrap">
                  <div className="sx-osint-consent">
                    <div className="sx-osint-consent-ttl">{kn ? "ಮುಕ್ತ-ಮೂಲ ಪರಿಶೀಲನೆ (OSINT)" : "Open-source checks (OSINT)"}</div>
                    {kn ? (
                      <p>
                        ಫೋನ್, UPI ಐಡಿ, ವಾಹನ, ಬ್ಯಾಂಕ್ ಖಾತೆ ಅಥವಾ IFSC, IMEI, ವೆಬ್‌ಸೈಟ್, ಇಮೇಲ್ ಅಥವಾ ಹೆಸರನ್ನು ಮುಕ್ತ ವೆಬ್ ಮತ್ತು ಸಾರ್ವಜನಿಕ ದಾಖಲೆಗಳಲ್ಲಿ ಪರಿಶೀಲಿಸಿ.
                        ನೀವು ಟೈಪ್ ಮಾಡುವ ಗುರುತು ಮಾತ್ರ ಹೊರಗೆ ಹೋಗುತ್ತದೆ: ಇದು <b>FIR ದಾಖಲೆಯನ್ನು ಎಂದಿಗೂ ಓದುವುದಿಲ್ಲ, ಬದಲಿಸುವುದಿಲ್ಲ</b>.
                        ನೀವು ದೃಢೀಕರಿಸುವವರೆಗೆ ಸಿಕ್ಕಿದ್ದೆಲ್ಲವೂ ಪರಿಶೀಲಿಸದ ಸುಳಿವು; ಪ್ರತಿ ಹುಡುಕಾಟ ನಿಮ್ಮ ಹೆಸರಿನಲ್ಲಿ ದಾಖಲಾಗುತ್ತದೆ.
                      </p>
                    ) : (
                      <p>
                        Check a phone number, UPI ID, vehicle, bank account or IFSC, IMEI, website, email or name against the open web and public registries.
                        Only the identifier you type leaves the building: this <b>never reads or changes the FIR record</b>.
                        Everything found is an unverified lead until you confirm it, and every search is logged against your name.
                      </p>
                    )}
                    <div className="sx-osint-consent-btns">
                      <button onClick={() => setProfileTab("details")} className="sx-act">{kn ? "ರದ್ದುಮಾಡಿ" : "Cancel"}</button>
                      <button onClick={() => setOsintAbout((v) => !v)} className="sx-act" aria-expanded={osintAbout}>
                        {osintAbout ? (kn ? "ಮರೆಮಾಡಿ" : "Hide details") : (kn ? "ಇನ್ನಷ್ಟು ತಿಳಿಯಿರಿ" : "Know more")}
                      </button>
                      <button
                        style={{ marginLeft: "auto" }}
                        onClick={() => {
                          setOsintConsentOpen(false);
                          setOsintAbout(false);
                          appendOsintAudit(`OSINT session authorized by ${getSessionOfficer()}`);
                        }}
                        className="sx-act primary"
                      >
                        {kn ? "ಅರ್ಥವಾಯಿತು · ಪ್ರಾರಂಭಿಸಿ" : "I understand · Start"}
                      </button>
                    </div>
                  </div>
                  <AnimatePresence initial={false}>
                  {osintAbout && (
                    <motion.div key="osint-about" style={{ overflow: "hidden" }}
                      initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }} transition={SPRING}>
                    <OsintDocs kn={kn} onTry={() => {
                      setOsintConsentOpen(false);
                      setOsintAbout(false);
                      appendOsintAudit(`OSINT session authorized by ${getSessionOfficer()}`);
                    }} />
                    </motion.div>
                  )}
                  </AnimatePresence>
                </div>
              )}

              {osintAllowed && !osintConsentOpen && (
                <div className="sx-osint-wrap">
                  <div className="sx-osint-main">
                    {/* LEFT: Standalone OSINT Query Builder */}
                    <div className="sx-qbuilder">
                      <div className="sx-ql"><span className="req" />{kn ? "ಏನನ್ನು ಪರಿಶೀಲಿಸಬೇಕು" : "What to check"}</div>
                      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: "6px" }}>
                        <input
                          className="sx-qfield"
                          style={{ flex: 1, paddingRight: "64px" }}
                          value={osintQuery}
                          onChange={(e) => setOsintQuery(e.target.value)}
                          placeholder={kn ? "ಫೋನ್, UPI, ವಾಹನ, IFSC, IMEI, ವೆಬ್‌ಸೈಟ್, ಹೆಸರು…" : "Phone, UPI, vehicle, IFSC, IMEI, website, name…"}
                          onKeyDown={(e) => { if (e.key === "Enter") runOsint(); }}
                        />
                        <div style={{ position: "absolute", right: "10px", display: "flex", alignItems: "center", gap: "4px" }}>
                          <button
                            type="button"
                            onClick={toggleOsintVoice}
                            title={osintRecording ? "Stop listening" : "Speak target identifier"}
                            style={{ width: 26, height: 26, borderRadius: "50%", border: "none", background: osintRecording ? "rgba(239,68,68,0.16)" : "rgba(255,255,255,0.06)", color: osintRecording ? "#F87171" : "#94A3B8", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
                          >
                            {osintRecording ? <MicOff size={13} /> : <Mic size={13} />}
                          </button>
                          {osintQuery && (
                            <button
                              type="button"
                              onClick={() => setOsintQuery("")}
                              title="Clear target"
                              style={{ width: 24, height: 24, borderRadius: "50%", border: "none", background: "rgba(255,255,255,0.06)", color: "#94A3B8", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
                            >
                              <X size={13} />
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="sx-ql">{kn ? "ಉದಾಹರಣೆಗಳು" : "Try an example"}</div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                        {[
                          { label: "KA-02-MJ-4821", val: "KA-02-MJ-4821", hint: "Karnataka RTO Plate" },
                          { label: "9845012345@ybl", val: "9845012345@ybl", hint: "UPI VPA + Mobile" },
                          { label: "+91 98450 67890", val: "+91 98450 67890", hint: "KA Telecom MSISDN" },
                          { label: "24BH4821AA", val: "24BH4821AA", hint: "Bharat Series Plate" },
                          { label: "Ramesh Gowda", val: "Ramesh Gowda", hint: "Named Subject" },
                          { label: "SBIN0040071", val: "SBIN0040071", hint: "Bank branch (IFSC)" },
                          { label: "490154203237518", val: "490154203237518", hint: "Handset IMEI" },
                          { label: "sbi-rewards.online", val: "sbi-rewards.online", hint: "Suspicious website" },
                        ].map((preset) => (
                          <button
                            key={preset.val}
                            type="button"
                            title={preset.hint}
                            onClick={() => runOsint(preset.val)}
                            style={{
                              fontFamily: "JetBrains Mono, monospace",
                              fontSize: "10px",
                              padding: "4px 8px",
                              borderRadius: "5px",
                              border: osintQuery === preset.val ? "1px solid #F8FAFC" : "1px solid rgba(255,255,255,0.1)",
                              background: osintQuery === preset.val ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.03)",
                              color: "#E2E8F0",
                              cursor: "pointer",
                            }}
                          >
                            {preset.label}
                          </button>
                        ))}
                      </div>

                      <div className="sx-ql">{kn ? "ಮೂಲಗಳು" : "Sources"}</div>
                      {(() => {
                        // matched on the English name (`key` when the answer came back in Kannada)
                        const liveUsed = (reconData?.live_checks || []).map((c) => c.key || c.name).join(" ");
                        const offUsed = (reconData?.official_checks || []).map((c) => c.key || c.name).join(" ");
                        const REG = kn ? [
                          ["RBI IFSC ಪಟ್ಟಿ", "IFSC, ಬ್ಯಾಂಕ್ ಖಾತೆ", /IFSC registry/],
                          ["ಡೊಮೇನ್ ನೋಂದಣಿ (WHOIS)", "ವೆಬ್‌ಸೈಟ್, ಇಮೇಲ್", /WHOIS/],
                          ["ಪ್ರಮಾಣಪತ್ರ ದಾಖಲೆ", "ವೆಬ್‌ಸೈಟ್", /certificates/i],
                          ["IMEI ಪರಿಶೀಲನಾ ಅಂಕಿ", "IMEI", /IMEI check/],
                        ] : [
                          ["RBI IFSC list", "IFSC, bank account", /IFSC registry/],
                          ["Domain registry (WHOIS)", "Website, email", /WHOIS/],
                          ["Certificate log", "Website", /certificates/i],
                          ["IMEI check digit", "IMEI", /IMEI check/],
                        ];
                        const OFF = kn ? [
                          ["I4C ಶಂಕಿತರ ದಾಖಲೆ", "ಫೋನ್, UPI, ಖಾತೆ, ವೆಬ್‌ಸೈಟ್", /I4C/],
                          ["ಸಂಚಾರ ಸಾಥಿ", "ಫೋನ್, IMEI", /Sanchar Saathi/],
                          ["ಇ-ಚಲನ್ ಮತ್ತು ವಾಹನ್", "ವಾಹನ", /eChallan|Vahan/],
                          ["ಇ-ಕೋರ್ಟ್ಸ್, ಇಂಡಿಯನ್ ಕಾನೂನ್", "ಹೆಸರು", /eCourts|Kanoon/],
                          ["MCA ಕಂಪನಿ ಹುಡುಕಾಟ", "ಹೆಸರು", /MCA/],
                          ["NCRP 1930", "UPI, ಬ್ಯಾಂಕ್ ಖಾತೆ", /NCRP/],
                          ["URLhaus, ವೇಬ್ಯಾಕ್", "ವೆಬ್‌ಸೈಟ್", /URLhaus|Wayback/],
                        ] : [
                          ["I4C Suspect Registry", "Phone, UPI, account, website", /I4C/],
                          ["Sanchar Saathi", "Phone, IMEI", /Sanchar Saathi/],
                          ["eChallan and Vahan", "Vehicle", /eChallan|Vahan/],
                          ["eCourts and Indian Kanoon", "Name", /eCourts|Kanoon/],
                          ["MCA company search", "Name", /MCA/],
                          ["NCRP 1930", "UPI, bank account", /NCRP/],
                          ["URLhaus and Wayback", "Website", /URLhaus|Wayback/],
                        ];
                        const row = ([nm, forWhat, re], used) => (
                          <li key={nm} className={reconData && re.test(used) ? "on" : ""}>
                            <i aria-hidden="true" /><span>{nm}</span><em>{forWhat}</em>
                          </li>
                        );
                        return (
                          <div className="osq">
                            <div className="osq-g">
                              <div className="osq-h"><b>{kn ? "ಮುಕ್ತ ವೆಬ್" : "Open web"}</b>
                                <span>{osintSources.length ? (kn ? "ಈ ಪುಟಗಳು ಮಾತ್ರ" : "only these kinds of page") : (kn ? "ಎಲ್ಲ ಪುಟಗಳು" : "every kind of page")}</span></div>
                              <div className="osq-chips">
                                {[
                                  ["news_archives", kn ? "ಸುದ್ದಿ" : "News"],
                                  ["court_records", kn ? "ನ್ಯಾಯಾಲಯ" : "Court and legal"],
                                  ["public_records", kn ? "ಸರ್ಕಾರಿ" : "Government"],
                                  ["social_media", kn ? "ಸಾಮಾಜಿಕ" : "Social media"],
                                  ["marketplace", kn ? "ಮಾರುಕಟ್ಟೆ" : "Marketplace"],
                                ].map(([key, label]) => (
                                  <button type="button" key={key} aria-pressed={osintSources.includes(key)}
                                          className={osintSources.includes(key) ? "on" : ""} onClick={() => toggleOsintSource(key)}>{label}</button>
                                ))}
                              </div>
                            </div>
                            <div className="osq-g">
                              <div className="osq-h"><b>{kn ? "ನೇರ ದಾಖಲೆ ಪರಿಶೀಲನೆ" : "Registries, checked live"}</b><span>{kn ? "ಅನ್ವಯಿಸಿದಾಗ" : "when they apply"}</span></div>
                              <ul className="osq-list">{REG.map((r) => row(r, liveUsed))}</ul>
                            </div>
                            <div className="osq-g">
                              <div className="osq-h"><b>{kn ? "ಅಧಿಕೃತ ಪೋರ್ಟಲ್‌ಗಳು" : "Official portals"}</b><span>{kn ? "ಫಲಿತಾಂಶದಲ್ಲಿ" : "listed in the results"}</span></div>
                              <ul className="osq-list">{OFF.map((r) => row(r, offUsed))}</ul>
                            </div>
                            {reconData && <p className="osq-note">{kn ? "ಬೆಳಗಿದವು ಈ ಹುಡುಕಾಟಕ್ಕೆ ಬಳಸಲಾಗಿದೆ." : "Lit: used for this search."}</p>}
                          </div>
                        );
                      })()}

                      <div className="sx-ql">{kn ? "ಎಷ್ಟು ಪುಟಗಳನ್ನು ಓದಬೇಕು" : "How many pages to keep"}</div>
                      <div className="sx-depth">
                        {[
                          { key: "surface", label: "3" },
                          { key: "standard", label: "5" },
                          { key: "deep", label: "8" },
                          { key: "full", label: "12" },
                        ].map((d) => (
                          <button
                            type="button"
                            key={d.key}
                            onClick={() => setOsintDepth(d.key)}
                            className={osintDepth === d.key ? "on" : ""}
                            title={kn ? `ಇದನ್ನು ಉಲ್ಲೇಖಿಸುವ ${d.label} ಪುಟಗಳವರೆಗೆ` : `Keep up to ${d.label} pages that mention it`}
                          >
                            {d.label}
                          </button>
                        ))}
                      </div>

                      <button type="button" className="sx-run" onClick={() => runOsint()} disabled={osintLoading}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
                        {osintLoading ? (kn ? "ಸ್ಕ್ಯಾನ್…" : "Scanning…") : (kn ? "OSINT ಹುಡುಕಾಟ ಚಲಾಯಿಸಿ" : "Run OSINT search")}
                      </button>

                      <div className="sx-legal">
                        <b>{kn ? "ಕಾನೂನು ಸೂಚನೆ:" : "How this is handled:"}</b>{" "}
                        {kn
                          ? "ಈ OSINT ಘಟಕವು ಸಂಪೂರ್ಣವಾಗಿ ಸ್ವತಂತ್ರವಾಗಿದೆ ಮತ್ತು FIR ಡೇಟಾಬೇಸ್ ಅನ್ನು ಎಂದಿಗೂ ಮುಟ್ಟುವುದಿಲ್ಲ. ಎಲ್ಲಾ ಫಲಿತಾಂಶಗಳು ಪರಿಶೀಲಿಸದವು."
                          : "Only the identifier leaves the building; no FIR record is read or changed. Everything found is an unverified lead until confirmed, and every search is logged."}
                      </div>

                      <div className="sx-audit">
                        <div className="t">{kn ? "ಸೆಶನ್ ಲೆಕ್ಕಪರಿಶೋಧನೆ" : "Session audit log"}</div>
                        <div className="row"><span className="ts">INIT</span> {getSessionOfficer()}</div>
                        {osintAuditLog.map((entry, idx) => (
                          <div key={idx} className="row">
                            <span className="ts">{entry.ts}</span> {entry.text}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* RIGHT: what the run found - the officer's summary first, then the detail */}
                    <div className="sx-osint-results">
                      {osintLoading && (
                        <div className="sx-osint-empty sx-osint-loading"><BrainLoader kn={kn} steps={OSINT_STEPS} orbs={OSINT_ORBS} /></div>
                      )}
                      {reconData && !osintLoading && (
                        <OsintReport
                          r={reconData}
                          web={osint}
                          loading={osintLoading}
                          kn={kn}
                          onAudit={appendOsintAudit}
                          onCopy={() => {
                            navigator.clipboard?.writeText(osintReportText(reconData, getSessionOfficer()));
                            appendOsintAudit(`Copied the lead sheet for "${reconData.query}"`);
                            flashToast(kn ? "ವರದಿ ನಕಲಿಸಲಾಗಿದೆ" : "Lead sheet copied");
                          }}
                        />
                      )}
                      {!reconData && !osintLoading && (
                        <div className="sx-osint-empty">
                          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
                          <p>
                            {kn
                              ? "ಫೋನ್, UPI, ವಾಹನ ಸಂಖ್ಯೆ, ಬ್ಯಾಂಕ್ ಖಾತೆ / IFSC, IMEI, ವೆಬ್‌ಸೈಟ್, ಇಮೇಲ್ ಅಥವಾ ಹೆಸರನ್ನು ನಮೂದಿಸಿ."
                              : "Enter a phone number, UPI ID, vehicle number, bank account or IFSC, IMEI, website, email, username or name. You get what it is, what the open web really says about it, live registry checks, the official portals to check next, and a draft notice."}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {profileTab !== "osint" && !selectedId && <div className="sx-detail-empty">{kn ? "ವಿವರಗಳಿಗಾಗಿ ಪ್ರೊಫೈಲ್ ಆಯ್ಕೆಮಾಡಿ" : "Select a record from the list to view full dossier"}</div>}
          {profileTab !== "osint" && selectedId && loadingProfile && !p && <div className="sx-detail-empty"><div className="signal-pulse" style={{ width: 180 }} /></div>}
          {profileTab !== "osint" && selectedId && p && (
            <div className="sx-dp-inner fade-rise" key={selectedId}>
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
                    <span className="b verified">
                      <ShieldCheck size={12} />
                      {kn ? "ಪರಿಶೀಲಿತ ದಾಖಲೆ" : "Verified record"}
                    </span>
                    <span className={`b r-${tierCls(p.risk_score || 0)}`}>{tier(p.risk_score || 0)} {kn ? "ಅಪಾಯ" : "risk"}</span>
                    <span className="b id">{p.suspect_id}</span>
                    {rec?.priors != null && <span className="b priors">{rec.priors} {kn ? "ಹಿಂದಿನ ಪ್ರಕರಣ" : rec.priors === 1 ? "earlier case" : "earlier cases"}</span>}
                    {rec?.status && <span className="b status">{rec.status}</span>}
                  </div>
                </div>
                <div className="sx-hero-risk">
                  <div className="num">{typeof p.risk_score === "number" ? p.risk_score.toFixed(1) : "—"}</div>
                  <div className="lbl">{kn ? "ಅಪಾಯ ಅಂಕ" : "RISK SCORE"}</div>
                  <div className="bar"><div className="f" style={{ width: `${p.risk_score || 0}%` }} /></div>
                </div>
              </div>

              <div className="sx-profile-tabs">
                <div className="sx-ptabs-left">
                  <button
                    type="button"
                    className={`sx-ptab ${profileTab === "details" ? "on" : ""}`}
                    onClick={() => setProfileTab("details")}
                  >
                    <Activity size={13} />
                    {profileTab === "details" && <motion.span layoutId="sx-ptab-line" className="sx-ptab-line" transition={SPRING} />}
                    <span>{kn ? "ವಿವರಗಳು ಮತ್ತು ಕೇಸ್‌ಫೈಲ್" : "Details & Casefile"}</span>
                  </button>
                  <button
                    type="button"
                    className={`sx-ptab osint ${profileTab === "osint" ? "on" : ""}`}
                    onClick={() => setProfileTab("osint")}
                  >
                    <Sparkles size={13} />
                    {profileTab === "osint" && <motion.span layoutId="sx-ptab-line" className="sx-ptab-line" transition={SPRING} />}
                    <span>{kn ? "ಸ್ವತಂತ್ರ OSINT ಮತ್ತು ಫಾರೆನ್ಸಿಕ್ಸ್" : "Open-source checks (OSINT)"}</span>
                  </button>
                </div>
                <div className="sx-ptabs-actions">
                  {role !== "Approver" && (
                    <button className="sx-act-sm" onClick={() => setWatchRequest(true)}
                            title={kn ? "ಮೇಲ್ವಿಚಾರಕರ ಅನುಮೋದನೆ ಅಗತ್ಯ" : "Requires supervising officer approval"}>
                      <ShieldCheck size={12} aria-hidden="true" /> {kn ? "ವೀಕ್ಷಣಾ ಪಟ್ಟಿ" : "Watchlist"}
                    </button>
                  )}
                  <button className="sx-act-sm" onClick={() => router.push(`/map?zone=${encodeURIComponent(p.address_zone || p.zone || "")}`)}>
                    <MapPin size={12} /> {kn ? "ನಕ್ಷೆ" : "Map"}
                  </button>
                  <button className="sx-act-sm" onClick={() => router.push(`/antar?q=${encodeURIComponent("Tell me about " + (p.full_name || ""))}`)}>
                    <Sparkles size={12} /> {kn ? "Antar ಕೇಳಿ" : "Ask Antar"}
                  </button>
                  <button className="sx-act-sm primary" onClick={() => router.push(`/antarBrain?suspect=${p.suspect_id}`)}>
                    <Brain size={12} /> {kn ? "ಮೆದುಳಿನಲ್ಲಿ ನೋಡಿ" : "Show in Brain"} <ArrowRight size={12} />
                  </button>
                </div>
              </div>
              
              {profileTab === "details" && rec && (
              <div className="sx-sections sx-casefile">
                {/* Key figures - four numbers an officer reads first */}
                <div className="sx-kpis sx-sec-full">
                  <div>
                    <div className="sx-kpi-hd">
                      <span>{kn ? "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು" : "Linked cases"}</span>
                      <FolderGit2 size={14} />
                    </div>
                    <b className={rec.linkedCases == null ? "none" : ""}>{rec.linkedCases ?? (kn ? "ದಾಖಲೆಯಲ್ಲಿಲ್ಲ" : "None on record")}</b>
                  </div>
                  <div>
                    <div className="sx-kpi-hd">
                      <span>{kn ? "ಕೊನೆಯ FIR ನಿಂದ" : "Since last FIR"}</span>
                      <Calendar size={14} />
                    </div>
                    <b className={rec.lastFirDays == null ? "none" : ""}>{sinceText(rec.lastFirDays, kn, true)}</b>
                  </div>
                  <div>
                    <div className="sx-kpi-hd">
                      <span>{kn ? "ಸಹಚರರು" : "Associates"}</span>
                      <Users size={14} />
                    </div>
                    <b>{p.associates?.length ?? 0}</b>
                  </div>
                  <div>
                    <div className="sx-kpi-hd">
                      <span>{kn ? "ಮೊದಲಿನ ಪ್ರಕರಣಗಳು" : "Prior counts"}</span>
                      <Hash size={14} />
                    </div>
                    <b>{rec.priors ?? "—"}</b>
                  </div>
                </div>

                {/* ROW 1 LEFT: Complete Record Details */}
                <div className="sx-sec">
                  <div className="sx-sec-t">{kn ? "ಪೂರ್ಣ ದಾಖಲೆ ವಿವರಗಳು" : "Complete record details"} <span className="cnt">{kn ? "ಪರಿಶೀಲಿತ" : "FIR registry"}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಶಂಕಿತ ಐಡಿ" : "Suspect ID"}</span><span className="v mono">{p.suspect_id}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಪೂರ್ಣ ಹೆಸರು" : "Full name"}</span><span className="v">{p.full_name}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಅಡ್ಡಹೆಸರು" : "Known alias"}</span><span className="v">{p.alias || (kn ? "ದಾಖಲಾಗಿಲ್ಲ" : "None recorded")}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಪ್ರಾಥಮಿಕ ವಲಯ" : "Primary zone"}</span><span className="v">{rec.zone || "—"}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಪ್ರಸ್ತುತ ಸ್ಥಿತಿ" : "Current status"}</span><span className="v">{rec.status || (kn ? "ಸಕ್ರಿಯ ದಾಖಲೆ" : "Active record")}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಹಿಂದಿನ ಪ್ರಕರಣಗಳು" : "Prior FIR count"}</span><span className="v">{rec.priors != null ? `${rec.priors} (${rec.priors === 1 ? "case" : "cases"})` : "0"}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು" : "Linked case files"}</span><span className="v">{rec.linkedCases != null ? `${rec.linkedCases} linked` : (kn ? "ದಾಖಲೆಯಲ್ಲಿಲ್ಲ" : "None on record")}</span></div>
                  <div className="sx-field"><span className="k">{kn ? "ಕೊನೆಯ ಚಟುವಟಿಕೆ" : "Last FIR activity"}</span><span className="v">{sinceText(rec.lastFirDays, kn)}</span></div>
                  {(p.age || p.gender) && <div className="sx-field"><span className="k">{kn ? "ಲಿಂಗ · ವಯಸ್ಸು" : "Demographics"}</span><span className="v">{[cap(p.gender), p.age && `${p.age} yrs`].filter(Boolean).join(" · ")}</span></div>}
                  {isSearch && row?.match_method && <div className="sx-field"><span className="k">{kn ? "ಹುಡುಕಾಟ ಹೊಂದಾಣಿಕೆ" : "Search match"}</span><span className="v mono">{matchWhy(row)?.txt || row.match_method}</span></div>}
                </div>

                {/* The FIRs that name this person, each one openable as a case */}
                <PersonCases id={p.suspect_id} kn={kn} />

                {/* The money trail around this person: accounts they hold, UPI IDs on their FIRs */}
                <PersonMoney id={p.suspect_id} kn={kn} />

                {/* ROW 1 RIGHT: Why this risk score - points each factor actually contributed */}
                {(p.risk_attributions || p.factors) && (
                  <div className="sx-sec">
                    <div className="sx-sec-t">{kn ? "ಈ ಅಪಾಯ ಅಂಕ ಏಕೆ" : "Why this risk score"} <span className="cnt">{kn ? "4 ಅಂಶಗಳು" : "4 factors · points"}</span></div>
                    <p className="sx-why-narrative">
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

                {/* ROW 2 LEFT: Modus operandi */}
                {rec.moText && (
                  <div className="sx-sec">
                    <div className="sx-sec-t">{kn ? "ಅಪರಾಧ ವಿಧಾನ (MO)" : "How they operate (MO)"} <span className="cnt">{kn ? "ಸಾರಾಂಶ" : "case summary"}</span></div>
                    <div className="sx-mo">{rec.moText}</div>
                  </div>
                )}

                {/* ROW 2 RIGHT: Recommended next steps */}
                <div className={`sx-sec ${!rec.moText ? "sx-sec-full" : ""}`}>
                  <div className="sx-sec-t">{kn ? "ಮುಂದಿನ ಹೆಜ್ಜೆಗಳು" : "Recommended next steps"} <span className="cnt">{p.leads?.length || 0} {kn ? "ಕ್ರಮಗಳು" : "actions"}</span></div>
                  {p.leads?.length ? (
                    <ul className="sx-leads">
                      {p.leads.slice(0, 4).map((l, i) => (
                        <li key={i} className="sx-lead-item">
                          <span className="sx-lead-idx">0{i + 1}</span>
                          <span>{l}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="sx-empty-sm">{kn ? "ಯಾವುದೇ ಸೂಚಿತ ಕ್ರಮವಿಲ್ಲ" : "No suggested actions for this record."}</div>
                  )}
                </div>

                {/* ROW 3: Known associates - opens their record in place */}
                <div className="sx-sec sx-sec-full">
                  <div className="sx-sec-t">{kn ? "ತಿಳಿದ ಸಹಚರರು" : "Known associates"} <span className="cnt">{p.associates?.length || 0} {kn ? "ಸಂಪರ್ಕಗಳು" : "co-accused links"}</span></div>
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

                {/* ROW 4: Cross-case matches - only ones strong enough to be worth reading */}
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
              {/* Bottom Actions */}
              <div className="sx-actions">
                {role !== "Approver" && (
                  <button className="sx-act hitl-request" onClick={() => setWatchRequest(true)}
                          title={kn ? "ಮೇಲ್ವಿಚಾರಕರ ಅನುಮೋದನೆ ಅಗತ್ಯ" : "Requires supervising officer approval"}>
                    <ShieldCheck size={13} aria-hidden="true" /> {kn ? "ವೀಕ್ಷಣಾ ಪಟ್ಟಿ ವಿನಂತಿ" : "Request watchlist"}
                  </button>
                )}
                <button className="sx-act" onClick={() => router.push(`/map?zone=${encodeURIComponent(p.address_zone || p.zone || "")}`)}>
                  <MapPin size={13} /> {kn ? "ನಕ್ಷೆಯಲ್ಲಿ" : "View on Map"}
                </button>
                <button className="sx-act" onClick={() => router.push(`/antar?q=${encodeURIComponent("Tell me about " + (p.full_name || ""))}`)}>
                  <Sparkles size={13} /> {kn ? "Antar ಕೇಳಿ" : "Ask Antar"}
                </button>
                <button className="sx-act primary" onClick={() => router.push(`/antarBrain?suspect=${p.suspect_id}`)}>
                  <Brain size={13} /> {kn ? "ಮೆದುಳಿನಲ್ಲಿ ನೋಡಿ" : "Show in Brain"} <ArrowRight size={13} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const MoneyTrail = dynamic(() => import("@/components/MoneyTrail"), { ssr: false });
const SocialInsights = dynamic(() => import("@/components/SocialInsights"), { ssr: false });

// People | Money trail: the two ways into a case from Search.
function SearchViews({ view, onChange, kn, osint = null }) {
  const tabs = [["people", kn ? "ವ್ಯಕ್ತಿಗಳು" : "People"], ["money", kn ? "ಹಣದ ಜಾಡು" : "Money trail"], ["social", kn ? "ಸಾಮಾಜಿಕ ಒಳನೋಟ" : "Social insights"]];
  return (
    <nav className="sx-views" role="tablist" aria-label={kn ? "ಹುಡುಕಾಟ ನೋಟ" : "Search view"}>
      {tabs.map(([k, label]) => (
        <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? "on" : ""}
                onClick={() => view !== k && onChange(k)}>{label}</button>
      ))}
      {/* Open-source checks open in the People view's right panel; only the identifier leaves */}
      {osint && (
        <button type="button" className={osint.on ? "on" : ""} aria-pressed={osint.on} onClick={osint.toggle} data-tool="osint"
                title={kn ? "OSINT FIR ಮಾರ್ಗದಿಂದ ಹೊರಗಿದೆ: ಅಂತರದ ಪ್ರತ್ಯೇಕ ಶಾಖೆ (ಕರೆದಾಗ ಮಾತ್ರ)" : "OSINT out of FIR: a different branch to Antar (only when called)"}>
          {kn ? "OSINT ವರ್ಕ್‌ಬೆಂಚ್" : "OSINT Workbench"}
        </button>
      )}
    </nav>
  );
}

const inr = (n) => {
  const v = Number(n) || 0;
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  return `₹${v.toLocaleString("en-IN")}`;
};

// The money trail around a person (GET /api/money/person/{id}): the accounts they hold and the
// UPI IDs on the FIRs that name them, each one step from the full trail.
function PersonMoney({ id, kn }) {
  const router = useRouter();
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!id) return;
    let alive = true;
    setD(null);
    fetch(`${API}/api/money/person/${encodeURIComponent(id)}`)
      .then((r) => (r.ok ? r.json() : { accounts: [], unavailable: r.status === 403 ? "role" : "error" }))
      .then((j) => { if (alive) setD(j); })
      .catch(() => { if (alive) setD({ accounts: [], unavailable: "error" }); });
    return () => { alive = false; };
  }, [id]);
  if (!d) return null;
  const how = { held: kn ? "ಈ ವ್ಯಕ್ತಿಯ ಖಾತೆ" : "Held by this person", on_fir: kn ? "ಇವರನ್ನು ಹೆಸರಿಸುವ FIR ನಲ್ಲಿನ UPI" : "UPI on an FIR naming them" };
  return (
    <div className="sx-sec">
      <div className="sx-sec-t">{kn ? "ಹಣದ ಜಾಡು" : "Money trail"} <span className="cnt">{d.accounts.length ? `${inr(d.total_in)} ${kn ? "ಒಳಗೆ" : "in"} · ${inr(d.total_out)} ${kn ? "ಹೊರಗೆ" : "out"}` : ""}</span></div>
      {d.unavailable === "role" ? (
        <div className="sx-empty-sm">{kn ? "ಹಣದ ಜಾಡಿಗೆ ಇನ್ಸ್‌ಪೆಕ್ಟರ್ ಅಥವಾ ಮೇಲಿನ ಪ್ರವೇಶ ಬೇಕು." : "The money trail needs Inspector access or above."}</div>
      ) : d.accounts.length === 0 ? (
        <div className="sx-empty-sm">{kn ? "ಈ ವ್ಯಕ್ತಿಗೆ ಸಂಬಂಧಿಸಿದ ಖಾತೆ ಹಣದ ಜಾಡಿನಲ್ಲಿ ಇಲ್ಲ." : "No account linked to this person in the money trail."}</div>
      ) : (
        <ul className="sx-money">
          {d.accounts.map((a) => (
            <li key={a.account_id}>
              <div className="top">
                <b>{a.account_id}</b>
                <span>{how[a.how]}</span>
              </div>
              <div className="nums">
                <span><em>{kn ? "ಒಳಗೆ" : "In"}</em> {inr(a.total_in)} <small>({a.count_in})</small></span>
                <span><em>{kn ? "ಹೊರಗೆ" : "Out"}</em> {inr(a.total_out)} <small>({a.count_out})</small></span>
                <span><em>{kn ? "ಸಂಪರ್ಕ ಖಾತೆಗಳು" : "Counterparties"}</em> {a.counterparties}</span>
              </div>
              {a.flags.length > 0 && <div className="flags">{a.flags.map((f) => <i key={f}>{f}</i>)}</div>}
              <button type="button" className="ui-btn ui-btn--secondary ui-btn--sm" onClick={() => router.push(`/search?view=money&account=${encodeURIComponent(a.account_id)}`)}>
                {kn ? "ಹಣವನ್ನು ಅನುಸರಿಸಿ" : "Follow the money"} →
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// The person's criminal history: the FIRs that name them (GET /api/profile/{id}/cases),
// newest first, each opening the full case.
function PersonCases({ id, kn }) {
  const router = useRouter();
  const [d, setD] = useState(null);
  const [all, setAll] = useState(false);
  useEffect(() => {
    if (!id) return;
    let alive = true;
    setD(null); setAll(false);
    fetch(`${API}/api/profile/${encodeURIComponent(id)}/cases`)
      .then((r) => (r.ok ? r.json() : null)).then((j) => { if (alive) setD(j || { cases: [] }); })
      .catch(() => { if (alive) setD({ cases: [] }); });
    return () => { alive = false; };
  }, [id]);
  if (!d) return null;
  const list = all ? d.cases : d.cases.slice(0, 8);
  return (
    <div className="sx-sec">
      <div className="sx-sec-t">{kn ? "ಈ ವ್ಯಕ್ತಿಯನ್ನು ಹೆಸರಿಸುವ FIR ಗಳು" : "FIRs naming this person"} <span className="cnt">{d.cases.length}{d.districts?.length > 1 ? (kn ? ` · ${d.districts.length} ಜಿಲ್ಲೆ` : ` · ${d.districts.length} districts`) : ""}</span></div>
      {d.cases.length === 0 ? (
        <div className="sx-empty-sm">{kn ? "ದಾಖಲೆಯಲ್ಲಿ ಈ ವ್ಯಕ್ತಿಯನ್ನು ಹೆಸರಿಸುವ FIR ಇಲ್ಲ." : "No FIR in the register names this person."}</div>
      ) : (
        <ul className="sx-cases">
          {list.map((c) => (
            <li key={c.fir_id}>
              <button type="button" onClick={() => router.push(`/case/${encodeURIComponent(c.fir_id)}`)} title={kn ? "ಪ್ರಕರಣ ತೆರೆಯಿರಿ" : "Open the case"}>
                <b>{c.crime || c.crime_type}</b>
                <span>{[c.date, c.station, c.district].filter(Boolean).join(" · ")}</span>
                <em>{[c.stage, c.role].filter(Boolean).join(" · ")}</em>
              </button>
            </li>
          ))}
        </ul>
      )}
      {d.cases.length > 8 && (
        <button type="button" className="sx-cases-all" onClick={() => setAll((v) => !v)}>
          {all ? (kn ? "ಕಡಿಮೆ ತೋರಿಸಿ" : "Show fewer") : (kn ? `ಎಲ್ಲ ${d.cases.length} ತೋರಿಸಿ` : `Show all ${d.cases.length}`)}
        </button>
      )}
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


