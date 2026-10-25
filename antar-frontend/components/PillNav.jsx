"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useLang } from "@/components/Providers";
import { BookOpen, MessageSquare, Brain, Map, TrendingUp, Search , ChevronDown, ChevronRight} from "lucide-react";
import OfficerSelector from "@/components/OfficerSelector";
import LangToggle from "@/components/LangToggle";
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
  // Scroll edge: once an area that sits under this floating nav is scrolled, its content
  // fades out as it passes beneath the nav instead of being cut by a hard line. Only areas
  // whose top is under the nav and that are actually scrolled get it (see .is-under-nav in
  // apple-feel.css); the map, the Brain canvas and an unscrolled page are left alone.
  useEffect(() => {
    const onScroll = (e) => {
      const el = e.target === document ? document.scrollingElement : e.target;
      if (!(el instanceof Element)) return;
      const navBottom = document.querySelector(".cx-pillnav")?.getBoundingClientRect().bottom || 60;
      const top = el.getBoundingClientRect().top;
      const under = el.scrollTop > 2 && top < navBottom;
      // Touch the class and the variable only when they change: writing them on every scroll
      // event restyled the whole scrolled area each tick, which is what made long pages judder.
      if (el.classList.contains("is-under-nav") !== under) el.classList.toggle("is-under-nav", under);
      if (under) {
        const edge = `${Math.max(24, Math.round(navBottom - top + 28))}px`;
        if (el.style.getPropertyValue("--nav-edge") !== edge) el.style.setProperty("--nav-edge", edge);
      }
    };
    document.addEventListener("scroll", onScroll, { capture: true, passive: true });
    return () => document.removeEventListener("scroll", onScroll, { capture: true });
  }, []);

  // This nav is mounted on every screen, so the poll ran on all of them, forever, even
  // with the tab in the background - 240 requests an hour for a badge that changes a
  // handful of times a day. It now sleeps while the tab is hidden and catches up on the
  // way back, and the `antar-hitl` event still updates it instantly when Approvals acts,
  // which is what actually keeps the number honest.
  useEffect(() => {
    let alive = true;
    let t = null;
    const pull = () => {
      if (!alive || document.hidden) return;
      fetchAPI("/api/hitl/stats")
        .then((s) => { if (alive) setHitlPending(s?.pending || 0); })
        .catch(() => {});
    };
    const start = () => { if (t === null) t = setInterval(pull, 60000); };
    const stop = () => { if (t !== null) { clearInterval(t); t = null; } };
    const onVis = () => { if (document.hidden) stop(); else { pull(); start(); } };

    pull();
    start();
    const onUpdate = (e) => setHitlPending(e.detail?.pending || 0);
    window.addEventListener("antar-hitl", onUpdate);
    document.addEventListener("visibilitychange", onVis);
    return () => {
      alive = false; stop();
      window.removeEventListener("antar-hitl", onUpdate);
      document.removeEventListener("visibilitychange", onVis);
    };
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
            transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease"
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
          transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease",
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
                transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease",
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
            transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease",
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
            transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease",
          }}
          onMouseOver={(e) => e.currentTarget.style.color = "#FFFFFF"}
          onMouseOut={(e) => e.currentTarget.style.color = "rgba(255, 255, 255, 0.55)"}
        >
          {kn ? "ನಮ್ಮ ಬಗ್ಗೆ" : "ABOUT"}
        </button>

        {/* EN | ಕನ್ನಡ: in the nav, so it is in the same place on every screen and covers nothing */}
        <LangToggle />

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
