"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { asset } from "@/lib/assets";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

// Global language (EN/KN) shared across the shell + pages (e.g. the Ask chat).
export const LangCtx = createContext({ lang: "en", setLang: () => {} });
export const useLang = () => useContext(LangCtx);

// Full product vision in the sidebar; live routes are links, the rest show "soon".
const NAV = [
  { href: "/ask", en: "Ask", kn: "ಪ್ರಶ್ನೆ", ico: "", live: true },
  { href: "/", en: "Overview", kn: "ಅವಲೋಕನ", ico: "", live: true },
  { href: "/map", en: "Map", kn: "ನಕ್ಷೆ", ico: "", live: true },
  { href: "/network", en: "Network", kn: "ಜಾಲ", ico: "", live: true },
  { href: "/trends", en: "Trends", kn: "ಪ್ರವೃತ್ತಿ", ico: "", live: true },
  { href: "/search?view=social", en: "Social", kn: "ಸಾಮಾಜಿಕ", ico: "", live: true },
  { href: "/predict", en: "Predict", kn: "ಮುನ್ಸೂಚನೆ", ico: "", live: true },
  { href: "/profiles", en: "Profiles", kn: "ವ್ಯಕ್ತಿಚಿತ್ರ", ico: "", live: true },
  { href: "/alerts", en: "Alerts", kn: "ಎಚ್ಚರಿಕೆ", ico: "", live: false },
];

export default function Shell({ children }) {
  const path = usePathname();
  const [alerts, setAlerts] = useState(0);
  const [lang, setLangState] = useState("en");
  const [open, setOpen] = useState(false);

  useEffect(() => { setLangState(localStorage.getItem("insti_lang") || "en"); }, []);
  useEffect(() => {
    fetch(`${API}/api/alerts`).then((r) => r.json()).then((d) => setAlerts(d.active || 0)).catch(() => {});
  }, [path]);
  useEffect(() => { setOpen(false); }, [path]);   // close the mobile drawer on navigation

  function setLang(l) {
    setLangState(l);
    try { localStorage.setItem("insti_lang", l); } catch {}
  }

  const cur = NAV.find((n) => n.href === path);
  const title = cur ? (lang === "kn" ? cur.kn : cur.en) : "Antar";

  return (
    <LangCtx.Provider value={{ lang, setLang }}>
      <div className="shell">
        {open && <div className="sidebar-backdrop" onClick={() => setOpen(false)} />}
        <aside className={`sidebar ${open ? "open" : ""} animate__animated animate__fadeInLeft animate__faster`}>
          <div className="brand">
            <div className="logo" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <img src={asset("/brand/antar_final_logo.png")} alt="Antar Icon" className="lg-brand-main-img" style={{ height: "36px", width: "36px", objectFit: "contain", filter: "drop-shadow(0 0 10px rgba(34,230,240,0.35))" }} />
              <span style={{ fontFamily: "'DotGothic16', monospace", fontWeight: 700, fontSize: "26px", letterSpacing: "0.08em", textTransform: "uppercase", textShadow: "0.6px 0 0 currentColor" }}>Antar</span>
            </div>
            <div className={`tagline ${lang === "kn" ? "kn" : ""}`} style={{ color: "rgba(255,255,255,0.6)", fontSize: "10px", fontWeight: 400, marginTop: "4px" }}>
              {lang === "kn" ? "ಆಲೋಚಿಸಿ. ಸಂಪರ್ಕಿಸಿ. ನಿರೀಕ್ಷಿಸಿ." : "thinking, connecting, and anticipating."}
            </div>
          </div>
          <nav className="nav">
            {NAV.map((n) =>
              n.live ? (
                <Link key={n.href} href={n.href} className={path === n.href ? "active" : ""}>
                  <span className="ico">{n.ico}</span>
                  <span className={lang === "kn" ? "kn" : ""}>{lang === "kn" ? n.kn : n.en}</span>
                </Link>
              ) : (
                <span key={n.href} className="navitem soon" title="Coming soon">
                  <span className="ico">{n.ico}</span>
                  <span className={lang === "kn" ? "kn" : ""}>{lang === "kn" ? n.kn : n.en}</span>
                  <span className="soon-tag">soon</span>
                </span>
              )
            )}
          </nav>
        </aside>

        <div className="main animate__animated animate__fadeIn animate__faster">
          <header className="topbar">
            <button className="hamburger" onClick={() => setOpen((o) => !o)} aria-label="Menu">Menu</button>
            <div className="page-title">{title}</div>
            <div className="spacer" />
            <div className="lang-toggle">
              <button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button>
              <button className={`kn ${lang === "kn" ? "active" : ""}`} onClick={() => setLang("kn")}>ಕನ್ನಡ</button>
            </div>
            <Link href="/predict" className="bell" title={`${alerts} active alert(s)`}>
              Alerts{alerts > 0 && <span className="badge-count">{alerts}</span>}
            </Link>

          </header>
          <div className="content">{children}</div>
        </div>
      </div>
    </LangCtx.Provider>
  );
}


