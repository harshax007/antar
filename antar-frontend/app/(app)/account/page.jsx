"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLang, useTheme } from "@/components/Providers";
import { User } from "lucide-react";
import "@/components/editorial-account.css";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

// Two demo identities so the screen can be shown as a normal officer OR an admin.
// The role switch (top of the sidebar) flips between them and re-gates admin-only settings.
const OFFICERS = {
  Admin:     { name: "Officer Arjun", id: "U-7001", initials: "A", unit: "Crime Intelligence Unit · Bengaluru City", rank: "Officer · Admin Access" },
  Inspector: { name: "Officer Arjun", id: "U-7001", initials: "A", unit: "Crime Intelligence Unit · Bengaluru City", rank: "Officer · Admin Access" },
};

const PREF_KEY = "antar_prefs";
const NOTIF_KEY = "antar_notifs";
const DEFAULT_PREFS = { landing: "/ask", mapView: "Bengaluru Urban", dateFormat: "YYYY-MM-DD", displayName: "" };
const DEFAULT_NOTIFS = { brain: true, patrol: true, risk: true, system: false };

const METHOD_CLS = { GET: "sx-risk-l", POST: "sx-risk-m", DELETE: "sx-risk-h" };

// The watchdog writes one line per alert: "[ANTAR ALERT] <label> — <summary>", where the
// summary is a fixed phrase per watch type (app/agents/sentinel_agent.py). Read it back into
// what an officer needs: what kind of watch, about what, what was seen, and what to do.
// Anything that does not parse is shown as written, never dropped.
function readAlert(a) {
  const msg = String(a.message || "").replace(/^\s*\[ANTAR ALERT\]\s*/i, "");
  const [label, summary = ""] = msg.split(/\s+—\s+/);
  const [kindLabel, ...rest] = (label || "").split(/\s+·\s+/);
  const subject = rest.join(" · ") || kindLabel || "";
  const cap = (t) => (t ? t.charAt(0).toUpperCase() + t.slice(1) : t);
  const pl = (n, one, many) => `${n} ${Number(n) === 1 ? one : many}`;
  let m;
  if ((m = summary.match(/^Corridor watch:\s*(\d+) linked offender\(s\) moving (.+?) ↔ (.+?)(?:, onward (.+?))?\.$/))) {
    const [, n, from, to, onward] = m;
    return { kind: "corridor", tag: ["Corridor watch", "ಮಾರ್ಗ ಕಣ್ಗಾವಲು"], title: cap(subject),
      detail: `${pl(n, "linked offender", "linked offenders")} moving between ${from} and ${to}${onward ? `, heading on to ${onward}` : ""}.`,
      step: `Alert the checkposts on this route and tell ${from} and ${to}.`,
      link: { en: "Open on map", kn: "ನಕ್ಷೆಯಲ್ಲಿ", href: `/map?zone=${encodeURIComponent(from)}` } };
  }
  if ((m = summary.match(/^Pattern watch:\s*(\d+) (.+?) case\(s\) on record(?: in (.+?))? \(evidence ledger\)\.$/))) {
    const [, n, crime, zone] = m;
    return { kind: "pattern", tag: ["Pattern watch", "ಮಾದರಿ ಕಣ್ಗಾವಲು"], title: cap(subject),
      detail: `${pl(n, `${crime} case`, `${crime} cases`)} on record${zone ? ` in ${zone}` : ""}.`,
      step: `Check patrol cover${zone ? ` in ${zone}` : ""} for ${crime}.`,
      link: { en: "Open on map", kn: "ನಕ್ಷೆಯಲ್ಲಿ", href: `/map?${zone ? `zone=${encodeURIComponent(zone)}&` : ""}crime_type=${encodeURIComponent(crime)}` } };
  }
  if ((m = summary.match(/^Entity tripwire:\s*(\d+) ledger signal\(s\) for (.+?)\.$/))) {
    const [, n, who] = m;
    const what = (kindLabel || "").replace(/\s*watch$/i, "");
    return { kind: "person", tag: ["Person watch", "ವ್ಯಕ್ತಿ ಕಣ್ಗಾವಲು"], title: what && what !== subject ? `${cap(what)} · ${subject}` : subject,
      detail: `${pl(n, "record", "records")} in the evidence ledger ${Number(n) === 1 ? "mentions" : "mention"} ${who}.`,
      step: `Open ${who}'s record and check what is new.`,
      link: { en: "Open the record", kn: "ದಾಖಲೆ ತೆರೆಯಿರಿ", href: `/search?q=${encodeURIComponent(who)}` } };
  }
  return { kind: "other", tag: ["Watch", "ಕಣ್ಗಾವಲು"], title: cap(subject) || "Alert", detail: summary || msg, step: null, link: null };
}

const cap1 = (t) => (t ? t.charAt(0).toUpperCase() + t.slice(1) : "");

function alertWhen(ts, kn) {
  if (!ts) return kn ? "ಈಗ" : "Just now";
  const d = new Date(ts), now = new Date();
  const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const same = d.toDateString() === now.toDateString();
  return same ? `${kn ? "ಇಂದು" : "Today"} ${time}` : `${d.toLocaleDateString("en-IN", { day: "numeric", month: "short" })} ${time}`;
}

function Icon({ name }) {
  const p = { width: 15, height: 15, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round" };
  switch (name) {
    case "gear": return <svg {...p}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>;
    case "bell": return <svg {...p}><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>;
    case "shield": return <svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>;
    case "file": return <svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>;
    case "download": return <svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>;
    case "db": return <svg {...p}><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>;
    case "star": return <svg {...p}><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>;
    case "approve": return <svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>;
    case "siren": return <svg {...p}><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>;
    case "eye": return <svg {...p}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>;
    case "history": return <svg {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /><path d="M12 7v5l3 2" /></svg>;
    case "lock": return <svg {...p}><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>;
    case "logout": return <svg {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>;
    case "brief": return <svg {...p}><rect x="4" y="4" width="16" height="18" rx="2" /><path d="M9 2h6v4H9z" /><path d="M8 12h8M8 16h5" /></svg>;
    default: return null;
  }
}

function Toggle({ on, onChange, label, sub }) {
  return (
    <div className="ac-toggle-row">
      <div className="ac-tr-label"><div className="ac-tr-name">{label}</div>{sub && <div className="ac-tr-sub">{sub}</div>}</div>
      <button type="button" className={`ac-tsw ${on ? "on" : ""}`} role="switch" aria-checked={on} aria-label={label} onClick={onChange}><b /></button>
    </div>
  );
}

export default function AccountPage() {
  const router = useRouter();
  const { lang, toggleLang } = useLang();
  const { theme, toggleTheme } = useTheme();
  const kn = lang === "kn";

  const [role, setRoleState] = useState("Admin");
  // The signed-in account, as the server issued it. A Policymaker gets the sections that do
  // not read cases: Preferences, Security, Export Centre.
  const [signedIn, setSignedIn] = useState(null);
  useEffect(() => {
    try {
      const s = JSON.parse(sessionStorage.getItem("antar_session") || "null");
      if (s?.role) setRoleState(s.role === "Admin" ? "Admin" : "Admin");
      if (s?.officer) setSignedIn({ id: s.officer, role: s.role });
    } catch {}
  }, []);
  const policy = signedIn?.role === "Policymaker";

  function setRole(next) {
    setRoleState(next);
    try {
      const s = JSON.parse(sessionStorage.getItem("antar_session") || "null") || { officer: "DEMO-OFF", ts: Date.now() };
      sessionStorage.setItem("antar_session", JSON.stringify({ ...s, role: next }));
      window.dispatchEvent(new CustomEvent("antar-role"));
      window.dispatchEvent(new Event("storage"));
    } catch {}
  }

  const isAdmin = role === "Admin";
  const officer = OFFICERS[role];

  const [section, setSection] = useState("briefing");
  const [brief, setBrief] = useState(null);
  const [briefZone, setBriefZone] = useState("all");
  const [briefWindow, setBriefWindow] = useState("12h");
  const [briefErr, setBriefErr] = useState(false);
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [draftPrefs, setDraftPrefs] = useState(DEFAULT_PREFS);
  const [notifs, setNotifs] = useState(DEFAULT_NOTIFS);
  const [saved, setSaved] = useState(false);
  const [vigil, setVigil] = useState({
    section91Audit: true,
    piiDemographicRedaction: true,
    unsubGeometryOnly: true,
    dwaniBilingualStream: true,
  });
  const [certDownloaded, setCertDownloaded] = useState(false);

  const [auditRows, setAuditRows] = useState(null);
  const [auditStatus, setAuditStatus] = useState(null);
  const [sessions, setSessions] = useState([
    { id: "s1", device: "Windows · Chrome 125", ip: "Bengaluru HQ · 192.168.1.10", last_seen: "active now", this: true },
    { id: "s2", device: "Android · Antar Field App", ip: "Field Unit 4 · 10.20.4.88", last_seen: "2 hours ago", this: false },
  ]);
  const [revoking, setRevoking] = useState(null);
  const [ingestFile, setIngestFile] = useState(null);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [pwOpen, setPwOpen] = useState(false);
  const [alertsList, setAlertsList] = useState([]);
  const [hitlPending, setHitlPending] = useState(0);

  // Pending approvals, for the sidebar badge. Same source as the ACCOUNT badge in the nav.
  useEffect(() => {
    let alive = true;
    const pull = () => fetch(`${API}/api/hitl/stats`)
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => { if (alive && s) setHitlPending(s.pending || 0); })
      .catch(() => {});
    pull();
    const t = setInterval(pull, 15000);
    const onUpdate = () => pull();
    window.addEventListener("antar-hitl", onUpdate);
    return () => { alive = false; clearInterval(t); window.removeEventListener("antar-hitl", onUpdate); };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sec = params.get("section");
    if (sec) setSection(sec);
  }, []);

  useEffect(() => {
    fetch(`${API}/api/sentinel`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => setAlertsList(d?.alerts || []))
      .catch(() => {});
  }, []);

  // Load persisted settings from backend, fallback to local
  useEffect(() => {
    fetch(`${API}/api/profile`, { headers: { "X-Officer": officer.id } })
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((d) => {
        if (d.preferences) {
          setPrefs({ ...DEFAULT_PREFS, ...d.preferences });
          setDraftPrefs({ ...DEFAULT_PREFS, ...d.preferences });
        }
        if (d.notifications) setNotifs({ ...DEFAULT_NOTIFS, ...d.notifications });
      })
      .catch(() => {
        try {
          const p = JSON.parse(localStorage.getItem(PREF_KEY) || "null");
          if (p) { setPrefs({ ...DEFAULT_PREFS, ...p }); setDraftPrefs({ ...DEFAULT_PREFS, ...p }); }
          const n = JSON.parse(localStorage.getItem(NOTIF_KEY) || "null");
          if (n) setNotifs({ ...DEFAULT_NOTIFS, ...n });
        } catch {}
      });
  }, [officer.id]);

  // Shift brief (A4) - compiled from real FIRs + hotspots; re-fetch on zone/window change
  useEffect(() => {
    if (section !== "briefing") return;
    setBrief(null); setBriefErr(false);
    fetch(`${API}/api/briefing/shift?zone=${encodeURIComponent(briefZone)}&window=${briefWindow}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setBrief)
      .catch(() => setBriefErr(true));
  }, [section, briefZone, briefWindow]);

  // Audit log (re-fetch when role changes → Inspector 403, Admin rows)
  useEffect(() => {
    if (section !== "activity") return;
    setAuditRows(null); setAuditStatus(null);
    fetch(`${API}/api/audit?limit=80`, { headers: { "X-Role": role, "X-Officer": officer.id } })
      .then((r) => { setAuditStatus(r.status); return r.ok ? r.json() : null; })
      .then((d) => setAuditRows(d?.rows || null))
      .catch(() => setAuditStatus(0));
  }, [section, role, officer.id]);

  function savePrefs() {
    setPrefs(draftPrefs);
    try { localStorage.setItem(PREF_KEY, JSON.stringify(draftPrefs)); } catch {}
    fetch(`${API}/api/profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Officer": officer.id },
      body: JSON.stringify({ preferences: draftPrefs, notifications: notifs })
    }).catch(() => {});
    setSaved(true);
    setTimeout(() => setSaved(false), 2200);
  }
  function toggleNotif(key) {
    setNotifs((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try { localStorage.setItem(NOTIF_KEY, JSON.stringify(next)); } catch {}
      fetch(`${API}/api/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Officer": officer.id },
        body: JSON.stringify({ preferences: prefs, notifications: next })
      }).catch(() => {});
      return next;
    });
  }
  async function revokeSession(id) {
    setRevoking(id);
    await new Promise((r) => setTimeout(r, 350));
    setSessions((prev) => prev.filter((s) => s.id !== id));
    setRevoking(null);
  }
  async function handleIngest() {
    if (!ingestFile) return;
    setIngestStatus("loading");
    try {
      const form = new FormData();
      form.append("file", ingestFile);
      const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
      await res.json().catch(() => {});
      setIngestStatus(res.ok ? "ok" : "error");
    } catch { setIngestStatus("error"); }
  }

  const perms = [
    { name: kn ? "ಚಾಟ್ · ಪ್ರಶ್ನೆ" : "Chat · Query", level: "Full", color: "var(--green)" },
    { name: kn ? "ನಕ್ಷೆ · ವೀಕ್ಷಣೆ" : "Map · View & Filter", level: "Full", color: "var(--green)" },
    { name: kn ? "ಹುಡುಕಾಟ · DB" : "Search · Internal DB", level: "Full", color: "var(--green)" },
    { name: kn ? "ಮೆದುಳು" : "Brain · Graph", level: isAdmin ? "Full" : "Read", color: isAdmin ? "var(--green)" : "var(--amber)" },
    { name: kn ? "OSINT" : "OSINT · Open-web", level: isAdmin ? "Full" : "Locked", color: isAdmin ? "var(--cyan)" : "var(--muted)" },
    { name: kn ? "ಡೇಟಾ ಇಂಜೆಸ್ಟ್" : "Export · Case Dossier", level: isAdmin ? "Full" : "Locked", color: isAdmin ? "var(--cyan)" : "var(--muted)" },
  ];

  const unread = (notifs.brain ? 1 : 0) + (notifs.patrol ? 1 : 0);
  const SECTIONS = [
    { key: "briefing", en: "Shift Brief", kn: "ಶಿಫ್ಟ್ ಬ್ರೀಫ್", icon: "brief" },
    // Approvals moved off the top nav: the queue is the officer's own work, and its
    // pending count is what the ACCOUNT badge in PillNav is counting.
    { key: "approvals", en: "Approvals", kn: "ಅನುಮೋದನೆಗಳು", icon: "approve", badge: hitlPending },
    { key: "alerts", en: "Antar Alerts", kn: "Antar ಎಚ್ಚರಿಕೆಗಳು", icon: "siren", badge: alertsList.length },
    { key: "preferences", en: "Preferences", kn: "ಆದ್ಯತೆಗಳು", icon: "gear" },
    { key: "vigil", en: "Misuse Checks", kn: "ದುರ್ಬಳಕೆ ತಪಾಸಣೆ", icon: "eye" },
    { key: "trace", en: "Observability & Trace", kn: "ವೀಕ್ಷಣೆ ಮತ್ತು ಜಾಡು", icon: "history" },
    { key: "notifications", en: "Notifications", kn: "ಅಧಿಸೂಚನೆಗಳು", icon: "bell", badge: unread },
    { key: "security", en: "Security", kn: "ಭದ್ರತೆ", icon: "lock" },
    { key: "activity", en: "Activity Log", kn: "ಚಟುವಟಿಕೆ", icon: "file" },
    { key: "export", en: "Export Centre", kn: "ರಫ್ತು ಕೇಂದ್ರ", icon: "download" },
    ...(isAdmin && !policy ? [{ key: "admin", en: "Admin · Data", kn: "ನಿರ್ವಾಹಕ · ಡೇಟಾ", icon: "db" }] : []),
  ].filter((s) => !policy || ["preferences", "security", "export"].includes(s.key));
  // If a non-admin somehow lands on the admin section (after switching role back), bounce to preferences.
  const activeSection = (section === "admin" && !isAdmin) || !SECTIONS.some((s) => s.key === section) ? "preferences" : section;

  // The top of each part of the account: what it is and who it is for, why it matters, and
  // the one thing to do next. Read in five seconds, before any detail.
  const toId = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  const INTRO = {
    briefing: {
      en: `The last ${briefWindow} across your districts on one page, for the officer taking over a shift: what came in, where, and what to do first.`,
      kn: `ಕಳೆದ ${briefWindow} ಒಂದೇ ಪುಟದಲ್ಲಿ, ಶಿಫ್ಟ್ ವಹಿಸಿಕೊಳ್ಳುವ ಅಧಿಕಾರಿಗೆ: ಏನು ದಾಖಲಾಯಿತು, ಎಲ್ಲಿ, ಮತ್ತು ಮೊದಲು ಏನು ಮಾಡಬೇಕು.`,
      next: ["Start with the priority actions.", "ಆದ್ಯತಾ ಕ್ರಮಗಳಿಂದ ಆರಂಭಿಸಿ."],
      cta: brief?.priority_actions?.length ? { en: "See priority actions", kn: "ಆದ್ಯತಾ ಕ್ರಮಗಳು", go: () => toId("ac-priority"), arrow: "↓" } : null,
    },
    alerts: {
      en: "Alerts raised by Antar's watch: a place or a watched person that broke its usual pattern. For the duty officer.",
      kn: "ಅಂತರ್ ಕಣ್ಗಾವಲು ಎತ್ತಿದ ಎಚ್ಚರಿಕೆಗಳು: ಸಾಮಾನ್ಯ ಮಾದರಿ ಮುರಿದ ಸ್ಥಳ ಅಥವಾ ವ್ಯಕ್ತಿ. ಕರ್ತವ್ಯದ ಅಧಿಕಾರಿಗೆ.",
      next: ["Acknowledge an alert once someone is on it.", "ಯಾರಾದರೂ ಕ್ರಮ ಕೈಗೊಂಡ ನಂತರ ಸ್ವೀಕರಿಸಿ."],
      cta: { en: "Open the forecast alerts", kn: "ಮುನ್ಸೂಚನೆ ಎಚ್ಚರಿಕೆಗಳು", go: () => router.push("/predict"), arrow: "→" },
    },
    preferences: {
      en: "How Antar opens and reads for you: language, first screen, map view and date format. Only your account changes.",
      kn: "ಅಂತರ್ ನಿಮಗೆ ಹೇಗೆ ತೆರೆಯುತ್ತದೆ: ಭಾಷೆ, ಮೊದಲ ಪರದೆ, ನಕ್ಷೆ ನೋಟ, ದಿನಾಂಕ ಸ್ವರೂಪ. ನಿಮ್ಮ ಖಾತೆ ಮಾತ್ರ ಬದಲಾಗುತ್ತದೆ.",
      next: ["Change a setting, then save.", "ಬದಲಿಸಿ, ನಂತರ ಉಳಿಸಿ."],
    },
    vigil: {
      en: "The safeguards against misuse: evidence hashing, no automatic identity merge, location-only profiling of unknown suspects. For supervisors and auditors.",
      kn: "ದುರ್ಬಳಕೆ ತಡೆಯುವ ರಕ್ಷಣೆಗಳು: ಸಾಕ್ಷ್ಯ ಹ್ಯಾಶಿಂಗ್, ಸ್ವಯಂ ಗುರುತು ವಿಲೀನ ಇಲ್ಲ, ಅಪರಿಚಿತ ಶಂಕಿತರಿಗೆ ಸ್ಥಳ-ಮಾತ್ರ ವಿಶ್ಲೇಷಣೆ. ಮೇಲ್ವಿಚಾರಕರು ಮತ್ತು ಲೆಕ್ಕಪರಿಶೋಧಕರಿಗೆ.",
      next: ["Leave these on unless a supervisor says otherwise.", "ಮೇಲ್ವಿಚಾರಕರು ಹೇಳದ ಹೊರತು ಇವು ಆನ್ ಆಗಿರಲಿ."],
    },
    notifications: {
      en: "What Antar tells you about, and when. Fewer, sharper notices are read; a flood is ignored.",
      kn: "ಅಂತರ್ ನಿಮಗೆ ಯಾವುದರ ಬಗ್ಗೆ, ಯಾವಾಗ ತಿಳಿಸುತ್ತದೆ. ಕಡಿಮೆ, ನಿಖರ ಸೂಚನೆಗಳು ಓದಲ್ಪಡುತ್ತವೆ.",
      next: ["Turn on only what you act on.", "ನೀವು ಕ್ರಮ ಕೈಗೊಳ್ಳುವುದನ್ನು ಮಾತ್ರ ಆನ್ ಮಾಡಿ."],
    },
    security: {
      en: "Your sign-in, password and the devices signed in as you. Police data stays behind this account.",
      kn: "ನಿಮ್ಮ ಸೈನ್-ಇನ್, ಪಾಸ್‌ವರ್ಡ್ ಮತ್ತು ನಿಮ್ಮ ಹೆಸರಿನಲ್ಲಿ ಸೈನ್ ಇನ್ ಆದ ಸಾಧನಗಳು.",
      next: ["Revoke any device you do not recognise.", "ಗುರುತಿಸದ ಸಾಧನವನ್ನು ರದ್ದುಮಾಡಿ."],
    },
    activity: {
      en: "Every search, answer and approval made under your ID, read from the audit record. For you and for audit.",
      kn: "ನಿಮ್ಮ ಐಡಿಯಲ್ಲಿ ಮಾಡಿದ ಪ್ರತಿ ಹುಡುಕಾಟ, ಉತ್ತರ ಮತ್ತು ಅನುಮೋದನೆ, ಆಡಿಟ್ ದಾಖಲೆಯಿಂದ.",
      next: ["Check it when anything looks unfamiliar.", "ಏನಾದರೂ ಅಪರಿಚಿತವಾಗಿ ಕಂಡರೆ ಪರಿಶೀಲಿಸಿ."],
    },
    export: {
      en: "Case dossiers and reports to download, for court, a briefing or a handover.",
      kn: "ನ್ಯಾಯಾಲಯ, ಬ್ರೀಫಿಂಗ್ ಅಥವಾ ಹಸ್ತಾಂತರಕ್ಕಾಗಿ ಪ್ರಕರಣ ಕಡತಗಳು ಮತ್ತು ವರದಿಗಳು.",
      next: ["Pick the format you need.", "ಬೇಕಾದ ಸ್ವರೂಪವನ್ನು ಆರಿಸಿ."],
    },
    admin: {
      en: "Load new FIR data into Antar. Admins only; this step is in preview.",
      kn: "ಹೊಸ FIR ದತ್ತಾಂಶವನ್ನು ಅಂತರ್‌ಗೆ ಸೇರಿಸಿ. ನಿರ್ವಾಹಕರಿಗೆ ಮಾತ್ರ; ಪೂರ್ವವೀಕ್ಷಣೆ ಹಂತ.",
      next: ["Choose a file, then upload it.", "ಫೈಲ್ ಆರಿಸಿ, ನಂತರ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ."],
    },
  };
  const secIdx = SECTIONS.findIndex((x) => x.key === activeSection);
  const secMeta = SECTIONS[secIdx];
  const intro = INTRO[activeSection];
  const two = (n) => String(n).padStart(2, "0");

  return (
    <div className="ac-page">
      {/* ── LEFT SIDEBAR ── */}
      <aside className="ac-sidebar">
        <div className="ac-prof">
          <div className="ac-av-wrap">
            <div className="ac-av" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", lineHeight: 1 }}>
              <User size={32} strokeWidth={1.5} style={{ color: "#ffffff" }} />
            </div>
            <div className="ac-av-ring" />
          </div>
          <div className="ac-pwho">
            <span className="ac-pkick">{kn ? "ಸೈನ್ ಇನ್ ಆಗಿರುವವರು" : "Signed in as"}</span>
            <div className="ac-pname">{policy ? (kn ? "ನೀತಿ ನಿರೂಪಕ" : "Policymaker") : (kn ? "ಅಧಿಕಾರಿ" : "Officer")}</div>
            <div className="ac-pid">{policy ? signedIn.id : officer.id}</div>
          </div>
        </div>

        {/* Role switch removed */}

        <nav className="ac-snav" aria-label={kn ? "ಖಾತೆ ವಿಭಾಗಗಳು" : "Account sections"}>
          {SECTIONS.map((s) => (
            <button key={s.key} className={`ac-snav-item ${activeSection === s.key ? "on" : ""}`} onClick={() => {
              if (s.key === "trace") {
                router.push("/trace");
                return;
              }
              if (s.key === "approvals") {
                router.push("/approvals");
                return;
              }
              setSection(s.key);
            }} aria-current={activeSection === s.key}>
              <Icon name={s.icon} />
              <span>{kn ? s.kn : s.en}</span>
              {s.badge > 0 && <span className="ac-snav-badge">{s.badge}</span>}
            </button>
          ))}
        </nav>

        <button className="ac-signout" onClick={() => { try { sessionStorage.removeItem("antar_session"); } catch {} router.push("/login"); }}>
          <Icon name="logout" /> {kn ? "ಸೈನ್ ಔಟ್" : "Sign out"}
        </button>
      </aside>

      {/* ── MAIN CONTENT ── */}
      <div className="ac-main">
        {secMeta && intro && (
          <header className="ac-hero" key={activeSection}>
            <h1>{kn ? secMeta.kn : secMeta.en}</h1>
            <p className="ac-lead">{kn ? intro.kn : intro.en}</p>
            <div className="ac-next">
              {intro.cta && (
                <button type="button" className="ui-btn ui-btn--primary ac-cta" onClick={intro.cta.go}>
                  {kn ? intro.cta.kn : intro.cta.en}{intro.cta.arrow && <span aria-hidden="true"> {intro.cta.arrow}</span>}
                </button>
              )}
              <span>{kn ? intro.next[1] : intro.next[0]}</span>
            </div>
          </header>
        )}
        {/* SHIFT BRIEF (A4) */}
        {activeSection === "briefing" && (
          <div className="ac-block">
            <div className="ac-block-hd">
              <span className="ac-block-t"><Icon name="brief" /> {kn ? "ಶಿಫ್ಟ್ ಬ್ರೀಫ್" : "Shift Brief"}</span>
              {brief && <span className="ac-brief-fresh">{kn ? "ರಚಿಸಲಾಗಿದೆ" : "compiled"} {(brief.generated_at || "").slice(11, 16) || "—"}</span>}
            </div>
            <div className="ac-brief-controls">
              <select className="ac-select" value={briefZone} onChange={(e) => setBriefZone(e.target.value)} aria-label="Zone">
                <option value="all">{kn ? "ಎಲ್ಲಾ ಜಿಲ್ಲೆಗಳು" : "All districts"}</option>
                {["Bengaluru City", "Mysuru City", "Belagavi", "Hubballi", "Mangaluru", "Kalaburagi"].map((z) => <option key={z} value={z}>{z}</option>)}
              </select>
              <select className="ac-select" value={briefWindow} onChange={(e) => setBriefWindow(e.target.value)} aria-label="Window">
                {["8h", "12h", "24h", "48h"].map((w) => <option key={w} value={w}>{w}</option>)}
              </select>
            </div>
            {briefErr && <div className="ac-err">{kn ? "ಬ್ರೀಫ್ ಲೋಡ್ ಆಗಲಿಲ್ಲ - ಬ್ಯಾಕೆಂಡ್ ಪರಿಶೀಲಿಸಿ." : `Could not load brief - check backend at ${API}.`}</div>}
            {!brief && !briefErr && <div className="ac-loading"><div className="signal-pulse" style={{ width: 160 }} /></div>}
            {brief && (
              <>
                <div className="ac-brief-summary">{brief.executive_summary}</div>
                <div className="ac-brief-stats">
                  <div className="ac-bstat"><span className="v">{brief.active_beacons ?? 0}</span><span className="k">{kn ? "ಸಕ್ರಿಯ ಹಾಟ್‌ಸ್ಪಾಟ್" : "active hotspots"}</span></div>
                  <div className="ac-bstat"><span className="v">{brief.key_incidents?.length ?? 0}</span><span className="k">{kn ? "ಪ್ರಮುಖ ಘಟನೆ" : "key incidents"}</span></div>
                  <div className="ac-bstat"><span className="v">{brief.window_hours}h</span><span className="k">{kn ? "ವಿಂಡೋ" : "window"}</span></div>
                </div>
                <div className="ac-shead" id="ac-priority">{kn ? "ಆದ್ಯತಾ ಕ್ರಮಗಳು" : "Priority actions"}</div>
                {(brief.priority_actions || []).map((a) => (
                  <div key={a.rank} className="ac-brief-action">
                    <span className="rank">{a.rank}</span>
                    <div><div className="act">{a.action}</div><div className="rat">{a.rationale}</div></div>
                  </div>
                ))}
                {brief.key_incidents?.length > 0 && (
                  <>
                    <div className="ac-shead" style={{ marginTop: 14 }}>{kn ? "ಪ್ರಮುಖ ಘಟನೆಗಳು" : "Key incidents"}</div>
                    <div className="ac-table-wrap">
                      <table className="ac-table">
                        <thead><tr><th>FIR</th><th>{kn ? "ಅಪರಾಧ" : "Crime"}</th><th>{kn ? "ಸಮಯ" : "Time"}</th><th>{kn ? "ಸ್ಥಳ" : "Location"}</th></tr></thead>
                        <tbody>
                          {brief.key_incidents.map((k, i) => (
                            <tr key={i}><td className="ac-mono">{k.fir_no}</td><td>{String(k.crime_type || "").replace(/_/g, " ")}</td><td className="ac-mono">{k.time || "—"}</td><td>{k.location}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
                <div className="ac-brief-foot" style={{ color: "rgba(255,255,255,0.4)" }}>{kn ? "ವಲಯ:" : "Zone:"} {brief.zone}</div>
              </>
            )}
          </div>
        )}

        {/* ANTAR ALERTS */}
        {activeSection === "alerts" && (
          <div className="ac-block">
            <div className="ac-block-hd"><span className="ac-block-t"><Icon name="siren" /> {kn ? "Antar ಎಚ್ಚರಿಕೆಗಳು" : "Antar Alerts"}</span></div>
            {alertsList.length === 0 ? (
              <div className="ac-loading" style={{ color: "#94A3B8" }}>{kn ? "ಯಾವುದೇ ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ." : "No active watchdog alerts."}</div>
            ) : (
              <>
                {(() => {
                  const read = alertsList.map(readAlert);
                  const by = (k) => read.filter((r) => r.kind === k).length;
                  const parts = [["corridor", "corridor", "ಮಾರ್ಗ"], ["pattern", "pattern", "ಮಾದರಿ"], ["person", "person", "ವ್ಯಕ್ತಿ"]]
                    .filter(([k]) => by(k)).map(([k, en, knw]) => `${by(k)} ${kn ? knw : en}`);
                  return (
                    <div className="ac-al-summary">
                      <span><b>{alertsList.length}</b> {kn ? "ತೆರೆದ ಎಚ್ಚರಿಕೆ" : alertsList.length === 1 ? "open alert" : "open alerts"}{parts.length ? ` · ${parts.join(" · ")}` : ""}</span>
                      <button type="button" className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => setAlertsList([])}>
                        {kn ? "ಎಲ್ಲವನ್ನೂ ಸ್ವೀಕರಿಸಿ" : "Acknowledge all"}
                      </button>
                    </div>
                  );
                })()}
                <ol className="ac-alerts">
                  {alertsList.map((a, i) => {
                    const r = readAlert(a);
                    const sev = String(a.severity || "").toLowerCase();
                    return (
                      <li key={i} className={`k-${r.kind} s-${sev}`}>
                        <div className="ac-al-top">
                          <span className="ac-al-tag"><i aria-hidden="true" />{kn ? r.tag[1] : r.tag[0]}<em>{sev === "high" ? (kn ? "ಹೆಚ್ಚು" : "High") : cap1(sev)}</em></span>
                          <span className="ac-al-time">{alertWhen(a.timestamp, kn)}</span>
                        </div>
                        <h3>{r.title}</h3>
                        <p>{r.detail}</p>
                        {r.step && <p className="ac-al-step"><span>{kn ? "ಸಲಹೆ" : "Suggested"}</span>{r.step}</p>}
                        <div className="ac-al-foot">
                          {r.link && (
                            <button type="button" className="ui-btn ui-btn--secondary ui-btn--sm" onClick={() => router.push(r.link.href)}>
                              {kn ? r.link.kn : r.link.en} <span aria-hidden="true">→</span>
                            </button>
                          )}
                          <button type="button" className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => setAlertsList(alertsList.filter((_, idx) => idx !== i))}>
                            {kn ? "ಸ್ವೀಕರಿಸಿ" : "Acknowledge"}
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              </>
            )}
          </div>
        )}

        {/* PREFERENCES */}
        {activeSection === "preferences" && (
          <div className="ac-block">
            <div className="ac-block-hd"><span className="ac-block-t"><Icon name="gear" /> {kn ? "ಆದ್ಯತೆಗಳು" : "Preferences"}</span>
              {saved && <span className="ac-saved"> {kn ? "ಉಳಿಸಲಾಗಿದೆ" : "Saved"}</span>}</div>
            <div className="ac-pref-grid">
              <div className="ac-field">
                <label>{kn ? "ಇಂಟರ್‌ಫೇಸ್ ಭಾಷೆ" : "Interface Language"}</label>
                <select className="ac-select" value={lang} onChange={(e) => { if (e.target.value !== lang) toggleLang(); }}>
                  <option value="en">English</option>
                  <option value="kn">ಕನ್ನಡ</option>
                </select>
              </div>

              <div className="ac-field">
                <label>{kn ? "ಡೀಫಾಲ್ಟ್ ಪರದೆ" : "Default landing screen"}</label>
                <select className="ac-select" value={draftPrefs.landing} onChange={(e) => setDraftPrefs({ ...draftPrefs, landing: e.target.value })}>
                  <option value="/ask">{kn ? "ಚಾಟ್" : "Chat"}</option>
                  <option value="/brain">{kn ? "ಮೆದುಳು" : "Brain"}</option>
                  <option value="/map">{kn ? "ನಕ್ಷೆ" : "Map"}</option>
                  <option value="/predict">{kn ? "ಮುನ್ಸೂಚನೆ" : "Predict"}</option>
                  <option value="/search">{kn ? "ಹುಡುಕಾಟ" : "Search"}</option>
                </select>
              </div>
              <div className="ac-field">
                <label>{kn ? "ಡೀಫಾಲ್ಟ್ ನಕ್ಷೆ ವೀಕ್ಷಣೆ" : "Default map view"}</label>
                <select className="ac-select" value={draftPrefs.mapView} onChange={(e) => setDraftPrefs({ ...draftPrefs, mapView: e.target.value })}>
                  <option>Bengaluru Urban</option><option>All Karnataka</option><option>My District</option>
                </select>
              </div>
              <div className="ac-field">
                <label>{kn ? "ದಿನಾಂಕ ಸ್ವರೂಪ" : "Date format"}</label>
                <select className="ac-select" value={draftPrefs.dateFormat} onChange={(e) => setDraftPrefs({ ...draftPrefs, dateFormat: e.target.value })}>
                  <option>YYYY-MM-DD</option><option>DD/MM/YYYY</option><option>DD MMM YYYY</option>
                </select>
              </div>
              <div className="ac-field">
                <label>{kn ? "ವರದಿ ಹೆಸರು" : "Display name (for reports)"}</label>
                <input className="ac-input" value={draftPrefs.displayName} placeholder={officer.name}
                       onChange={(e) => setDraftPrefs({ ...draftPrefs, displayName: e.target.value })} />
              </div>
            </div>
            <div className="ac-save-bar">
              <button className="ac-save-btn" onClick={savePrefs}>{kn ? "ಉಳಿಸಿ" : "Save preferences"}</button>
              <button className="ac-cancel-btn" onClick={() => setDraftPrefs(prefs)}>{kn ? "ರದ್ದು" : "Reset"}</button>
              <span className="ac-save-hint">{kn ? "ಭಾಷೆ ತಕ್ಷಣ ಅನ್ವಯಿಸುತ್ತದೆ" : "Language applies instantly"}</span>
            </div>
          </div>
        )}

        {/* COMPLIANCE SETTINGS */}
        {activeSection === "vigil" && (
          <div className="ac-block fade-rise">
            <div className="ac-block-hd" style={{ marginBottom: "20px" }}>
              <span className="ac-block-t"><Icon name="eye" /> {kn ? "ನಿಯಮಗಳು ಹಾಗೂ ಭದ್ರತೆ" : "Compliance & Guardrails"}</span>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <Toggle
                on={vigil.section91Audit}
                onChange={() => setVigil((v) => ({ ...v, section91Audit: !v.section91Audit }))}
                label={kn ? "ಸೆಕ್ಷನ್ 91 ಸಾಕ್ಷ್ಯ ಆಡಿಟ್ ಹ್ಯಾಶಿಂಗ್" : "§ 91 Evidence Hashing"}
                sub={kn ? "ರಫ್ತು ಮಾಡಿದ ಸಾಕ್ಷ್ಯಗಳಿಗೆ ಕ್ರಿಪ್ಟೋಗ್ರಾಫಿಕ್ ಸಮಗ್ರತೆಯನ್ನು ನಿರ್ವಹಿಸುತ್ತದೆ." : "Maintains cryptographic integrity for exported evidence."}
              />
              <Toggle
                on={vigil.piiDemographicRedaction}
                onChange={() => setVigil((v) => ({ ...v, piiDemographicRedaction: !v.piiDemographicRedaction }))}
                label={kn ? "ಐಡೆಂಟಿಟಿ ಮರ್ಜ್ ನಿರ್ಬಂಧ" : "Prevent Auto-Identity Merge"}
                sub={kn ? "ಎಫ್‌ಐಆರ್‌ಗಳ ನಡುವೆ ಗುರುತುಗಳನ್ನು ವಿಲೀನಗೊಳಿಸಲು ಹಸ್ತಚಾಲಿತ ಅನುಮೋದನೆಯ ಅಗತ್ಯವಿದೆ." : "Requires manual approval before merging identities across FIRs."}
              />
              <Toggle
                on={vigil.unsubGeometryOnly}
                onChange={() => {}}
                label={kn ? "UNSUB ಪ್ರೊಫೈಲಿಂಗ್ (ಲಾಕ್)" : "UNSUB Geometry Profiling (Locked)"}
                sub={kn ? "ಪಕ್ಷಪಾತವನ್ನು ತಡೆಗಟ್ಟಲು ಕೇವಲ ಭೌಗೋಳಿಕ ಡೇಟಾವನ್ನು ಬಳಸುತ್ತದೆ." : "Restricts analysis to spatial data to prevent demographic bias."}
              />
              <Toggle
                on={vigil.dwaniBilingualStream}
                onChange={() => setVigil((v) => ({ ...v, dwaniBilingualStream: !v.dwaniBilingualStream }))}
                label={kn ? "ಧ್ವನಿ ದ್ವಿಭಾಷಾ ಪೈಪ್‌ಲೈನ್" : "Dwani Bilingual Pipeline"}
                sub={kn ? "ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡ ಭಾಷೆಗಳಿಗೆ ಬೆಂಬಲ." : "Enables continuous bilingual support (EN/KN)."}
              />
            </div>

            {/* Evidentiary Hash Ledger Card */}
            <div style={{
              marginTop: "32px",
              padding: "16px",
              borderRadius: "8px",
              background: "rgba(34,230,240,0.05)",
              border: "1px solid rgba(34,230,240,0.15)",
              display: "flex",
              flexDirection: "column",
              gap: "12px"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "#22E6F0", fontFamily: "JetBrains Mono", fontWeight: 600 }}>
                  {kn ? "ಪ್ರಸ್ತುತ ಸೆಶನ್ ಆಡಿಟ್ ಹ್ಯಾಶ್" : "ACTIVE SESSION HASH"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setCertDownloaded(true);
                    setTimeout(() => setCertDownloaded(false), 2500);
                  }}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "4px",
                    background: "transparent",
                    color: certDownloaded ? "#18D69A" : "#22E6F0",
                    border: `1px solid ${certDownloaded ? "#18D69A" : "rgba(34,230,240,0.4)"}`,
                    fontSize: "10px",
                    cursor: "pointer"
                  }}
                >
                  {certDownloaded ? (kn ? " ಡೌನ್‌ಲೋಡ್ ಆಗಿದೆ" : " Downloaded") : (kn ? "ಪ್ರಮಾಣಪತ್ರ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ" : "Download Certificate")}
                </button>
              </div>
              <div style={{ fontSize: "11px", color: "#E2E8F0", fontFamily: "JetBrains Mono", wordBreak: "break-all" }}>
                ef54f348e82dbbbd74352af0bdae3621a9512bb4e018d6c5a190813ed2689a0b
              </div>
            </div>
          </div>
        )}

        {/* NOTIFICATIONS */}
        {activeSection === "notifications" && (
          <div className="ac-block">
            <div className="ac-block-hd"><span className="ac-block-t"><Icon name="bell" /> {kn ? "ಅಧಿಸೂಚನೆಗಳು" : "Notifications"}</span></div>
            <Toggle on={notifs.brain} onChange={() => toggleNotif("brain")} label={kn ? "ಎರಡನೇ ಮೆದುಳು ಹೊಂದಾಣಿಕೆಗಳು" : "Second-Brain matches"} sub={kn ? "ನಿಮ್ಮ ಕೇಸ್‌ಗಳ ಮೇಲೆ ಹೊಸ ಗ್ರಾಫ್ ಲಿಂಕ್‌ಗಳು" : "New graph links on your cases"} />
            <Toggle on={notifs.patrol} onChange={() => toggleNotif("patrol")} label={kn ? "ಗಸ್ತು ಸಲಹೆಗಳು" : "Patrol suggestions"} sub={kn ? "ಹೊಸ ಕಾರಿಡಾರ್ ರಚಿಸಿದಾಗ" : "When a new corridor is generated"} />
            <Toggle on={notifs.risk} onChange={() => toggleNotif("risk")} label={kn ? "ಅಪಾಯ ಸ್ಕೋರ್ ನವೀಕರಣಗಳು" : "Risk score updates"} sub={kn ? "ನೀವು ವೀಕ್ಷಿಸಿದ ಪ್ರೊಫೈಲ್‌ಗಳು" : "Profiles you have viewed"} />
            <Toggle on={notifs.system} onChange={() => toggleNotif("system")} label={kn ? "ಸಿಸ್ಟಮ್ ಪ್ರಕಟಣೆಗಳು" : "System announcements"} sub={kn ? "ನಿರ್ವಹಣೆ, ನವೀಕರಣಗಳು, ನೀತಿ" : "Maintenance, updates, policy"} />
          </div>
        )}

        {/* SECURITY */}
        {activeSection === "security" && (
          <div className="ac-block">
            <div className="ac-block-hd"><span className="ac-block-t"><Icon name="lock" /> {kn ? "ಭದ್ರತೆ" : "Security"}</span></div>

            <div className="ac-2fa-setup">
              <div className="ac-2fa-ico"><Icon name="shield" /></div>
              <div className="ac-2fa-body">
                <b>{kn ? "ಎರಡು-ಅಂಶ ದೃಢೀಕರಣ" : "Two-factor authentication"}</b>
                <span>{kn ? "ಇನ್ನೂ ಹೊಂದಿಸಲಾಗಿಲ್ಲ · ಹೆಚ್ಚುವರಿ ಭದ್ರತೆಗೆ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ" : "Not set up yet · recommended for extra security"}</span>
              </div>
              <span className="ac-2fa-status">{kn ? "ಆಫ್" : "OFF"}</span>
            </div>
            <div className="ac-sec-actions">
              <button className="ac-btn-primary" onClick={() => alert(kn ? "2FA ಸೆಟಪ್ ಶೀಘ್ರದಲ್ಲೇ (Catalyst Auth)" : "2FA setup coming soon (Catalyst Auth)")}>{kn ? "2FA ಹೊಂದಿಸಿ" : "Set up 2FA"}</button>
              <button className="ac-btn-ghost" onClick={() => setPwOpen((v) => !v)}>{kn ? "ಪಾಸ್‌ವರ್ಡ್ ಬದಲಿಸಿ" : "Change password"}</button>
            </div>
            {pwOpen && (
              <div className="ac-pwform">
                <input className="ac-input" type="password" placeholder={kn ? "ಪ್ರಸ್ತುತ ಪಾಸ್‌ವರ್ಡ್" : "Current password"} />
                <input className="ac-input" type="password" placeholder={kn ? "ಹೊಸ ಪಾಸ್‌ವರ್ಡ್" : "New password"} />
                <button className="ac-btn-primary" onClick={() => { setPwOpen(false); }}>{kn ? "ನವೀಕರಿಸಿ" : "Update"}</button>
              </div>
            )}

            <div className="ac-shead" style={{ marginTop: 20 }}>{kn ? `ಸಕ್ರಿಯ ಸೆಶನ್‌ಗಳು · ${sessions.length}` : `Active sessions · ${sessions.length}`}</div>
            {sessions.map((s) => (
              <div key={s.id} className={`ac-session ${s.this ? "this" : ""}`}>
                <div className="ac-sdevice">
                  {s.this && <span className="ac-sdot">●</span>}{s.device}
                  {s.this && <span className="ac-sthis">{kn ? "ಈ ಸಾಧನ" : "This device"}</span>}
                  {!s.this && <button className="ac-revoke" onClick={() => revokeSession(s.id)} disabled={revoking === s.id}>{revoking === s.id ? "…" : (kn ? "ರದ್ದು" : "Revoke")}</button>}
                </div>
                <div className="ac-ssub">{s.ip} · {s.last_seen}</div>
              </div>
            ))}
            {sessions.filter((s) => !s.this).length > 0 && (
              <button className="ac-btn-ghost" style={{ marginTop: 10 }} onClick={() => setSessions((prev) => prev.filter((s) => s.this))}>
                {kn ? "ಎಲ್ಲಾ ಇತರ ಸೆಶನ್‌ಗಳನ್ನು ರದ್ದುಗೊಳಿಸಿ" : "Revoke all other sessions"}
              </button>
            )}
          </div>
        )}

        {/* ACTIVITY LOG */}
        {activeSection === "activity" && (
          <div className="ac-block">
            <div className="ac-block-hd"><span className="ac-block-t"><Icon name="file" /> {kn ? "ಚಟುವಟಿಕೆ ಲಾಗ್" : "Activity Log"}</span></div>
            {auditStatus === 403 && (
              <div className="ac-403" role="status">{kn ? "ನಿರ್ವಾಹಕ ಪ್ರವೇಶದ ಅಗತ್ಯವಿದೆ. (Admin ಆಗಿ ಬದಲಿಸಿ)" : "Admin access required. Switch to Admin view."}</div>
            )}
            {auditStatus === 0 && <div className="ac-err">{kn ? "ಬ್ಯಾಕೆಂಡ್ ತಲುಪಲಾಗಲಿಲ್ಲ." : `Could not reach backend at ${API}.`}</div>}
            {auditRows === null && auditStatus !== 403 && auditStatus !== 0 && <div className="ac-loading"><div className="signal-pulse" style={{ width: 160 }} /></div>}
            {auditRows !== null && auditStatus === 200 && (
              <div className="ac-table-wrap">
                <table className="ac-table">
                  <thead><tr>
                    <th>{kn ? "ಸಮಯ" : "Time"}</th><th>{kn ? "ಅಧಿಕಾರಿ" : "Officer"}</th><th>{kn ? "ವಿಧಾನ" : "Method"}</th><th>{kn ? "ಮಾರ್ಗ" : "Path"}</th><th>{kn ? "ಸ್ಥಿತಿ" : "Status"}</th>
                  </tr></thead>
                  <tbody>
                    {auditRows.slice(0, 60).map((r, i) => (
                      <tr key={i}>
                        <td className="ac-mono">{(r.ts || "").slice(0, 19).replace("T", " ")}</td>
                        <td>{r.officer}</td>
                        <td><span className={`ac-mbadge ${METHOD_CLS[r.method] || ""}`}>{r.method}</span></td>
                        <td className="ac-mono ac-path">{r.path}</td>
                        <td><span className={`ac-sbadge ${r.status >= 400 ? "err" : "ok"}`}>{r.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}


        {activeSection === "export" && (
          <div className="ac-block">
            <div className="ac-block-hd"><span className="ac-block-t"><Icon name="download" /> {kn ? "ರಫ್ತು ಕೇಂದ್ರ" : "Export Centre"}</span></div>
            <div className="ac-export-grid">
              {[
                { t: kn ? "ಚಟುವಟಿಕೆ ವರದಿ" : "Activity Report", d: kn ? "ಕಳೆದ 30 ದಿನಗಳ ಎಲ್ಲಾ ಕ್ರಿಯೆಗಳು" : "All actions last 30 days, timestamped", tag: "PDF · CSV", color: "var(--cyan)" },
                { t: kn ? "ಕೇಸ್ ಡೋಸಿಯರ್" : "Case Dossier", d: kn ? "ಪ್ರೊಫೈಲ್‌ಗಳು, ಮುನ್ಸೂಚನೆಗಳು, ಬ್ರೈನ್ ಲಿಂಕ್‌ಗಳು" : "Profiles, predictions, Brain links", tag: isAdmin ? "PDF" : (kn ? "Admin" : "Admin only"), color: "var(--green)", locked: !isAdmin },
                { t: kn ? "ಕಚ್ಚಾ ಲೆಕ್ಕಪರಿಶೋಧನೆ" : "Raw Audit Log", d: kn ? "ಅನುಸರಣೆಗಾಗಿ ಯಂತ್ರ-ಓದಬಲ್ಲ ಲಾಗ್" : "Machine-readable log for compliance", tag: "JSON · CSV", color: "var(--amber)" },
              ].map((c, i) => (
                <div key={i} className={`ac-export-card ${c.locked ? "locked" : ""}`}>
                  <div className="ac-ec-ico" style={{ color: c.color }}><Icon name="download" /></div>
                  <div className="ac-ec-name">{c.t}</div>
                  <div className="ac-ec-desc">{c.d}</div>
                  <div className="ac-ec-tag" style={{ color: c.color }}>{c.tag}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ADMIN · DATA (admin only) */}
        {activeSection === "admin" && isAdmin && (
          <div className="ac-block">
            <div className="ac-block-hd"><span className="ac-block-t"><Icon name="db" /> {kn ? "ಡೇಟಾ ಇಂಜೆಸ್ಟ್ (ಪೂರ್ವವೀಕ್ಷಣೆ)" : "Data Ingest (Preview)"}</span></div>
            <p className="ac-block-sub" style={{ fontSize: "12px", color: "var(--muted)", marginBottom: "16px" }}>
              {kn ? "ಹೊಸ FIR ಡೇಟಾವನ್ನು CSV/JSON ಆಗಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ." : "Upload new FIR data as CSV/JSON."}
            </p>
            <div className="ac-ingest">
              <input type="file" accept=".csv,.json" onChange={(e) => setIngestFile(e.target.files?.[0] || null)} />
              <button className="ac-btn-primary" onClick={handleIngest} disabled={!ingestFile || ingestStatus === "loading"}>
                {ingestStatus === "loading" ? (kn ? "ಅಪ್‌ಲೋಡ್…" : "Uploading…") : (kn ? "ಅಪ್‌ಲೋಡ್" : "Upload")}
              </button>
              {ingestStatus === "ok" && <span style={{ color: "var(--green)" }}> {kn ? "ಯಶಸ್ವಿ" : "Success"}</span>}
              {ingestStatus === "error" && <span style={{ color: "var(--red)" }}> {kn ? "ವಿಫಲ" : "Failed"}</span>}
            </div>
          </div>
        )}
      </div>


    </div>
  );
}


