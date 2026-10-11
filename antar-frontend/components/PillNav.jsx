"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useLang } from "@/components/Providers";
import { BookOpen, MessageSquare, Brain, Map, TrendingUp, Search , ChevronDown, ChevronRight} from "lucide-react";
import OfficerSelector from "@/components/OfficerSelector";
import { asset } from "@/lib/assets";
import { fetchAPI } from "@/lib/api";

export default function PillNav() {
  const path = usePathname() || "";
  const router = useRouter();
  const { lang, toggleLang } = useLang();
  const kn = lang === "kn";
  const [navHidden, setNavHidden] = useState(false);

  // Pending human-in-the-loop decisions, for the APPROVALS badge. Polled lightly, and
  // refreshed instantly when the Approvals screen reports a change.
  const [hitlPending, setHitlPending] = useState(0);
  useEffect(() => {
    let alive = true;
    const pull = () => fetchAPI("/api/hitl/stats").then((s) => { if (alive) setHitlPending(s?.pending || 0); }).catch(() => {});
    pull();
    const t = setInterval(pull, 15000);
    const onUpdate = (e) => setHitlPending(e.detail?.pending || 0);
    window.addEventListener("antar-hitl", onUpdate);
    return () => { alive = false; clearInterval(t); window.removeEventListener("antar-hitl", onUpdate); };
  }, []);

  if (path === "/docs" || path?.startsWith("/docs/") || path === "/app/docs" || path?.startsWith("/app/docs/") || path?.includes("/docs")) {
    return null;
  }

  if (navHidden) {
    return (
            <div
        style={{
          position: "fixed",
          top: "12px",
          left: "24px",
          zIndex: 100000,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: "8px"
        }}
      >
        <button
          type="button"
          onClick={() => setNavHidden(false)}
          title={kn ? "ನ್ಯಾವಿಗೇಷನ್ ತೋರಿಸಿ" : "Show navigation"}
          style={{
            background: "rgba(11, 18, 32, 0.9)",
            border: "1px solid rgba(34, 230, 240, 0.4)",
            borderRadius: "50%",
            width: "38px",
            height: "38px",
            padding: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            boxShadow: "0 4px 20px rgba(0,0,0,0.5), inset 0 1px 1px rgba(255,255,255,0.1)",
            transition: "all 0.2s ease"
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.transform = "scale(1.05)";
            e.currentTarget.style.boxShadow = "0 6px 24px rgba(0,0,0,0.7), 0 0 15px rgba(34,230,240,0.3)";
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.transform = "scale(1)";
            e.currentTarget.style.boxShadow = "0 4px 20px rgba(0,0,0,0.5), inset 0 1px 1px rgba(255,255,255,0.1)";
          }}
        >
          <img
            src={asset("/brand/logo/antar_icon_white.png")}
            alt="Antar"
            style={{
              height: "20px",
              width: "20px",
              objectFit: "contain",
              filter: "drop-shadow(0 0 8px rgba(34,230,240,0.6))",
            }}
          />
        </button>
        <ChevronRight size={14} strokeWidth={3} color="#22E6F0" style={{ filter: "drop-shadow(0 0 4px rgba(34,230,240,0.5))" }} />
      </div>
    );
  }

  const switchScreen = (href) => {
    if (path === href) return;
    window.dispatchEvent(new CustomEvent("screen-switch", { detail: href }));
  };

  const links = [
    { en: "CHAT", kn: "ಚಾಟ್", href: "/antar" },
    { en: "BRAIN", kn: "ಮೆದುಳು", href: "/antarBrain" },
    { en: "MAP", kn: "ನಕ್ಷೆ", href: "/map" },
    { en: "PREDICT", kn: "ಮುನ್ಸೂಚನೆ", href: "/predict" },
    { en: "SEARCH", kn: "ಹುಡುಕಾಟ", href: "/search" },
  ];
  // APPROVALS used to sit here. It now lives inside Account (the queue is personal to the
  // officer, not a screen of the investigation), and its pending count rides on ACCOUNT.

  return (
    <nav
      className="cx-pillnav"
      aria-label="Primary Navigation"
      style={{
        position: "fixed",
        top: "10px",
        left: 0,
        right: 0,
        margin: "0 auto",
        width: "calc(100% - 40px)",
        maxWidth: "1280px",
        background: "rgba(6, 11, 20, 0.08)",
        backdropFilter: "blur(20px) saturate(160%)",
        WebkitBackdropFilter: "blur(20px) saturate(160%)",
        border: "1px solid rgba(34, 230, 240, 0.12)",
        boxShadow: "0 4px 24px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.05)",
        borderRadius: "9999px",
        padding: "6px 24px",
        display: "grid",
        gridTemplateColumns: "1fr auto 1fr",
        alignItems: "center",
        zIndex: 100000,
      }}
    >
      {/* Left: Antar Logo Icon with ANTAR and LIVE APP text underneath linking to /antar */}
      <div
        onClick={() => switchScreen("/antar")}
        style={{
          cursor: "pointer",
          display: "flex",
          justifySelf: "start",
          flexDirection: "column",
          alignItems: "center",
          gap: "2px",
          padding: "2px 6px",
          borderRadius: "8px",
          transition: "all 0.2s ease",
        }}
        title="Launch Live Antar Intelligence App (/antar)"
      >
        <img
          src={asset("/brand/logo/antar_icon_white.png")}
          alt="Antar Icon"
          style={{
            height: "15px",
            width: "15px",
            objectFit: "contain",
            filter: "drop-shadow(0 0 8px rgba(34,230,240,0.4))",
          }}
        />
        <span
          style={{
            fontFamily: "'DotGothic16', 'Silkscreen', monospace",
            fontSize: "10px",
            fontWeight: 700,
            letterSpacing: "0.2em",
            color: "#FFFFFF",
            lineHeight: 1,
          }}
        >
          ANTAR
        </span>
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "6.5px",
            fontWeight: 500,
            letterSpacing: "0.14em",
            color: "#86EFAC",
            lineHeight: 1,
            textShadow: "0 0 6px rgba(134, 239, 172, 0.4)",
          }}
        >
          LIVE APP
        </span>
      </div>

      {/* Center: Same Font as Think/Connect/Anticipate. On a phone this row becomes the
          tab bar at the bottom of the screen (globals.css, "Responsive"). */}
      <div
        className="cx-pill-center"
        style={{
          display: "flex",
          alignItems: "center",
          justifySelf: "center",
          gap: "36px",
        }}
      >
        {links.map((item) => {
          const active =
            path === item.href ||
            (item.href !== "/antar" && path.startsWith(`${item.href}/`)) ||
            (item.href === "/antar" && path === "/antar");
          return (
            <button
              key={item.en}
              type="button"
              className="cx-pill-link"
              aria-current={active ? "page" : undefined}
              onClick={() => switchScreen(item.href)}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: active ? "2px solid #22E6F0" : "2px solid transparent",
                color: active ? "#FFFFFF" : "rgba(255, 255, 255, 0.55)",
                fontFamily: "'DotGothic16', 'Silkscreen', monospace",
                fontSize: "11.5px",
                fontWeight: 700,
                letterSpacing: "0.16em",
                padding: "4px 2px",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              {kn ? item.kn : item.en}
            </button>
          );
        })}
      </div>

      <div className="cx-pill-right" style={{ display: "flex", alignItems: "center", justifySelf: "end", gap: "12px" }}>
        <OfficerSelector pending={hitlPending} />

        <button
          type="button"
          className="cx-pill-aux"
          onClick={() => switchScreen("/docs")}
          style={{
            background: "transparent",
            border: "none",
            color: "rgba(255, 255, 255, 0.55)",
            fontFamily: "'Inter', sans-serif",
            fontSize: "10.5px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            
            padding: "4px 8px",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
          onMouseOver={(e) => e.currentTarget.style.color = "#FFFFFF"}
          onMouseOut={(e) => e.currentTarget.style.color = "rgba(255, 255, 255, 0.55)"}
        >
          {kn ? "ಡಾಕ್ಸ್" : "DOCS"}
        </button>

        <button
          type="button"
          className="cx-pill-aux"
          onClick={() => switchScreen("/about")}
          style={{
            background: "transparent",
            border: "none",
            color: "rgba(255, 255, 255, 0.55)",
            fontFamily: "'Inter', sans-serif",
            fontSize: "10.5px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            
            padding: "4px 8px",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
          onMouseOver={(e) => e.currentTarget.style.color = "#FFFFFF"}
          onMouseOut={(e) => e.currentTarget.style.color = "rgba(255, 255, 255, 0.55)"}
        >
          {kn ? "ನಮ್ಮ ಬಗ್ಗೆ" : "ABOUT"}
        </button>

        <button
          type="button"
          className="cx-pill-hide"
          onClick={() => setNavHidden(true)}
          title={kn ? "ನ್ಯಾವಿಗೇಷನ್ ಮರೆಮಾಡಿ" : "Hide navigation"}
          aria-label="Hide navigation"
          style={{
            background: "transparent",
            border: "none",
            color: "#64748B",
            cursor: "pointer",
            padding: "4px 6px",
            fontSize: "11px",
          }}
        >
          ▴
        </button>
      </div>
    </nav>
  );
}
