"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useLang } from "@/components/Providers";
import { User } from "lucide-react";
import { readSession } from "@/lib/auth";
import "@/components/editorial-account.css";

const API = process.env.NEXT_PUBLIC_API_URL || "";

const OFFICERS = {
  Admin:     { name: "Officer Arjun", id: "U-7001", initials: "A", unit: "Crime Intelligence Unit · Bengaluru City", rank: "Officer · Admin Access" },
  Inspector: { name: "Officer Arjun", id: "U-7001", initials: "A", unit: "Crime Intelligence Unit · Bengaluru City", rank: "Officer · Admin Access" },
};

function Icon({ name }) {
  const p = { width: 15, height: 15, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round" };
  switch (name) {
    case "gear": return <svg {...p}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>;
    case "bell": return <svg {...p}><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>;
    case "shield": return <svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>;
    case "file": return <svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>;
    case "download": return <svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>;
    case "db": return <svg {...p}><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>;
    case "star": return <svg {...p}><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>;
    case "approve": return <svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>;
    case "logout": return <svg {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>;
    case "brief": return <svg {...p}><rect x="2" y="7" width="20" height="14" rx="2" ry="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" /></svg>;
    case "siren": return <svg {...p}><path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6l2.1 2.1M5.6 18.4l2.1-2.1m8.6-8.6l2.1-2.1" /><circle cx="12" cy="12" r="4" /></svg>;
    case "eye": return <svg {...p}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>;
    case "history": return <svg {...p}><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 14 14" /><path d="M3.05 11a9 9 0 0 1 .5-2m-.5 2h4" /></svg>;
    case "lock": return <svg {...p}><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>;
    default: return null;
  }
}

export default function AccountSidebar({
  activeSection = "briefing",
  onSelectSection,
  hitlBadge: initialHitl,
  alertsBadge: initialAlerts,
  notifsBadge: initialNotifs,
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { lang } = useLang();
  const kn = lang === "kn";

  const [role, setRole] = useState("Inspector");
  const [hitlPending, setHitlPending] = useState(initialHitl || 0);
  const [alertsCount, setAlertsCount] = useState(initialAlerts || 0);
  const [unreadCount, setUnreadCount] = useState(initialNotifs || 0);

  useEffect(() => {
    const s = readSession();
    if (s?.role) setRole(s.role);

    // Read initial pending hitl actions
    fetch(`${API}/api/hitl/stats`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d?.pending != null) setHitlPending(d.pending); })
      .catch(() => {});

    // Read alerts count
    fetch(`${API}/api/alerts?limit=20`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => {
        const arr = Array.isArray(d) ? d : d?.alerts || [];
        if (arr.length) setAlertsCount(arr.length);
      })
      .catch(() => {});

    // Read notifications count from storage
    try {
      const raw = localStorage.getItem("antar_notifs");
      if (raw) {
        const parsed = JSON.parse(raw);
        setUnreadCount((parsed.brain ? 1 : 0) + (parsed.patrol ? 1 : 0));
      }
    } catch {}

    function onHitl(e) {
      if (e?.detail?.pending != null) setHitlPending(e.detail.pending);
    }
    window.addEventListener("antar-hitl", onHitl);
    return () => window.removeEventListener("antar-hitl", onHitl);
  }, []);

  const isAdmin = role === "Admin";
  const officer = OFFICERS[role] || OFFICERS.Inspector;

  const hitlVal = initialHitl != null ? initialHitl : hitlPending;
  const alertsVal = initialAlerts != null ? initialAlerts : alertsCount;
  const notifsVal = initialNotifs != null ? initialNotifs : unreadCount;

  const SECTIONS = [
    { key: "briefing", en: "Shift Brief", kn: "ಶಿಫ್ಟ್ ಬ್ರೀಫ್", icon: "brief" },
    { key: "approvals", en: "Approvals", kn: "ಅನುಮೋದನೆಗಳು", icon: "approve", badge: hitlVal },
    { key: "alerts", en: "Antar Alerts", kn: "Antar ಎಚ್ಚರಿಕೆಗಳು", icon: "siren", badge: alertsVal },
    { key: "preferences", en: "Preferences", kn: "ಆದ್ಯತೆಗಳು", icon: "gear" },
    { key: "vigil", en: "Misuse Checks", kn: "ದುರ್ಬಳಕೆ ತಪಾಸಣೆ", icon: "eye" },
    { key: "trace", en: "Observability & Trace", kn: "ವೀಕ್ಷಣೆ ಮತ್ತು ಜಾಡು", icon: "history" },
    { key: "notifications", en: "Notifications", kn: "ಅಧಿಸೂಚನೆಗಳು", icon: "bell", badge: notifsVal },
    { key: "security", en: "Security", kn: "ಭದ್ರತೆ", icon: "lock" },
    { key: "activity", en: "Activity Log", kn: "ಚಟುವಟಿಕೆ", icon: "file" },
    { key: "export", en: "Export Centre", kn: "ರಫ್ತು ಕೇಂದ್ರ", icon: "download" },
    ...(isAdmin ? [{ key: "admin", en: "Admin · Data", kn: "ನಿರ್ವಾಹಕ · ಡೇಟಾ", icon: "db" }] : []),
  ];

  function handleNav(key) {
    if (key === "trace") {
      if (pathname === "/trace") return;
      router.push("/trace");
      return;
    }
    if (key === "approvals") {
      if (pathname === "/approvals") return;
      router.push("/approvals");
      return;
    }
    if (pathname === "/account" && onSelectSection) {
      onSelectSection(key);
    } else {
      router.push(key === "briefing" ? "/account" : `/account?section=${key}`);
    }
  }

  return (
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
          <div className="ac-pname">{kn ? "ಅಧಿಕಾರಿ" : "Officer"}</div>
          <div className="ac-pid">{officer.id}</div>
        </div>
      </div>

      <nav className="ac-snav" aria-label={kn ? "ಖಾತೆ ವಿಭಾಗಗಳು" : "Account sections"}>
        {SECTIONS.map((s) => (
          <button
            key={s.key}
            className={`ac-snav-item ${activeSection === s.key ? "on" : ""}`}
            onClick={() => handleNav(s.key)}
            aria-current={activeSection === s.key}
          >
            <Icon name={s.icon} />
            <span>{kn ? s.kn : s.en}</span>
            {s.badge > 0 && <span className="ac-snav-badge">{s.badge}</span>}
          </button>
        ))}
      </nav>

      <button
        className="ac-signout"
        onClick={() => {
          try { sessionStorage.removeItem("antar_session"); } catch {}
          router.push("/login");
        }}
      >
        <Icon name="logout" /> {kn ? "ಸೈನ್ ಔಟ್" : "Sign out"}
      </button>
    </aside>
  );
}
