"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLang, useTheme } from "@/components/Providers";
import DemoOverlay, { toggleDemoMode } from "@/components/DemoOverlay";
import ScreenTransition3D from "@/components/ScreenTransition3D";
import PillNav from "@/components/PillNav";
import GlobalGuide from "@/components/GlobalGuide";
import { Menu, X, Sun, Moon, User } from "lucide-react";
import { readSession, isValidSession, clearSession } from "@/lib/auth";
import { lowerCurtain } from "@/lib/curtain";

const NAV = [
  { href: "/antar",               en: "Chat",         kn: "ಪ್ರಶ್ನೆ" },
  { href: "/antarBrain",          en: "Brain",        kn: "ಮೆದುಳು" },
  { href: "/map",                 en: "Map",          kn: "ನಕ್ಷೆ" },
  { href: "/predict",             en: "Predict",      kn: "ಮುನ್ಸೂಚನೆ" },
  { href: "/search",              en: "Search",       kn: "ಹುಡುಕಾಟ" },
  { href: "/docs",                en: "Docs",         kn: "ದಾಖಲೆಗಳು" },
];

export { readSession };

export default function AppShell({ children }) {
  const path = usePathname();
  const router = useRouter();
  const { lang, toggleLang } = useLang();
  const { theme, toggleTheme } = useTheme();
  const kn = lang === "kn";
  const isCustomNav = path === "/ask" || path?.startsWith("/ask/") ||
                      path === "/antar" || path?.startsWith("/antar/") ||
                      path === "/docs" || path?.startsWith("/docs/") ||
                      path === "/info" || path?.startsWith("/info/") ||
                      path === "/guide" || path?.startsWith("/guide/") ||
                      path === "/login/guide" || path?.startsWith("/login/guide");
  const isChat = isCustomNav;

  const [session, setSession] = useState(null);
  const [expert, setExpert] = useState(false);
  const [menu, setMenu] = useState(false);
  const [navigatingTo, setNavigatingTo] = useState(null);

  useEffect(() => {
    function checkSession() {
      const s = readSession();
      // Two-account build: anything other than a known U-7001 (Admin) or U-9001 (Approver)
      // session (no session, or an old "Officer" one left in this tab) goes back to login. AppShell only wraps
      // the (app) routes, so this can never redirect /login into itself.
      if (!isValidSession(s)) {
        clearSession();
        router.replace("/login");
        return;
      }
      setSession(s);
      // Arriving from sign-in: the screen is on its way in, so the curtain can go - after a
      // beat, so what is under it has been painted first.
      setTimeout(lowerCurtain, 120);
      try { setExpert(localStorage.getItem("antar_expert") === "1"); } catch {}
    }
    checkSession();
    window.addEventListener("antar-role", checkSession);
    window.addEventListener("storage", checkSession);

    // Prefetch every other screen - but AFTER this one is interactive, and only when the
    // connection can afford it. Firing all six on mount pulled roughly a megabyte of
    // route chunks (recharts, xyflow, the 3D graph bundles) in parallel with the assets
    // the CURRENT page still needed, which is the opposite of what prefetching is for.
    // requestIdleCallback defers it to genuine idle time; the Save-Data / 2g checks skip
    // it entirely on a constrained connection.
    const conn = typeof navigator !== "undefined" ? navigator.connection : null;
    const frugal = !!conn && (conn.saveData || /(^|-)2g$/.test(conn.effectiveType || ""));
    let idleId;
    if (!frugal) {
      const run = () => NAV.forEach((n) => { try { router.prefetch(n.href); } catch {} });
      idleId = typeof window.requestIdleCallback === "function"
        ? window.requestIdleCallback(run, { timeout: 3000 })
        : setTimeout(run, 1500);
    }

    return () => {
      window.removeEventListener("antar-role", checkSession);
      window.removeEventListener("storage", checkSession);
      if (idleId != null) {
        if (typeof window.cancelIdleCallback === "function") window.cancelIdleCallback(idleId);
        else clearTimeout(idleId);
      }
    };
  }, [router]);

  // Smooth reset after route path updates
  useEffect(() => {
    const timer = setTimeout(() => setNavigatingTo(null), 200);
    return () => clearTimeout(timer);
  }, [path]);

  useEffect(() => {
    const fn = (e) => {
      const targetHref = e.detail;
      if (path === targetHref) return;
      setNavigatingTo(targetHref);
      // The overlay takes 180 ms to cover the screen; waiting 600 made every switch feel slow.
      setTimeout(() => {
        router.push(targetHref);
      }, 200);
    };
    window.addEventListener("screen-switch", fn);
    return () => window.removeEventListener("screen-switch", fn);
  }, [path, router]);

  function handleScreenSwitch(e, targetHref) {
    if (path === targetHref) return;
    e.preventDefault();
    setNavigatingTo(targetHref);
    setTimeout(() => {
      router.push(targetHref);
    }, 200);
  }

  const isAdmin = session?.role === "Admin";
  const officerName = session?.role === "Admin" ? "Admin Rao" : "Inspector Sharma";
  const initials = session?.role === "Admin" ? "AR" : "RS";

  function toggleExpert() {
    const next = !expert;
    setExpert(next);
    try { localStorage.setItem("antar_expert", next ? "1" : "0"); } catch {}
    window.dispatchEvent(new CustomEvent("antar-expert", { detail: { on: next } }));
  }

  return (
    <div className="ax-shell">
      {/* Global Unified Glassmorphism Pill Nav for All Screens */}
      <PillNav />

      {/* Global Contextual Help/Guide Button */}
      <GlobalGuide />

      {/* 3D Glassmorphic Screen Switching Overlay */}
      <ScreenTransition3D targetPath={navigatingTo} lang={lang} />

      <main className="ax-main" style={{ transition: "opacity 0.15s ease" }}>{children}</main>
      <DemoOverlay />
    </div>
  );
}
