"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLang, useTheme } from "@/components/Providers";
import { asset } from "@/lib/assets";
import { ADMIN_ID, signIn, homeFor } from "@/lib/auth";
import { raiseCurtain } from "@/lib/curtain";

const COPY = {
  en: {
    tag: "Think. Connect. Anticipate.", badge: "User ID", pw: "Password", auth: "Authenticate",
    verifying: "Verifying credentials…", granted: "Access granted", empty: "Enter your User ID and password to continue.",
    demoT: "Demo credentials", officer: "Officer", admin: "Admin", anyPw: "any password",
    bad: "User ID or password is incorrect.",
    locked: "Too many failed attempts. Wait a few minutes and try again.",
    down: "The server could not be reached. Check that the backend is running.",
    off: "Sign-in is not set up on this server yet.",
  },
  kn: {
    tag: "ಯೋಚಿಸಿ. ಸಂಪರ್ಕಿಸಿ. ನಿರೀಕ್ಷಿಸಿ.", badge: "ಬಳಕೆದಾರ ID", pw: "ಗುಪ್ತಪದ", auth: "ದೃಢೀಕರಿಸಿ",
    verifying: "ರುಜುವಾತುಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…", granted: "ಪ್ರವೇಶ ನೀಡಲಾಗಿದೆ", empty: "ಮುಂದುವರಿಯಲು ನಿಮ್ಮ ಬಳಕೆದಾರರ ಐಡಿ ಮತ್ತು ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ.",
    demoT: "ಡೆಮೊ ರುಜುವಾತುಗಳು", officer: "ಅಧಿಕಾರಿ", admin: "ನಿರ್ವಾಹಕ", anyPw: "ಯಾವುದೇ ಪಾಸ್‌ವರ್ಡ್",
    bad: "ಬಳಕೆದಾರ ID ಅಥವಾ ಪಾಸ್‌ವರ್ಡ್ ತಪ್ಪಾಗಿದೆ.",
    locked: "ಹಲವು ವಿಫಲ ಪ್ರಯತ್ನಗಳು. ಕೆಲವು ನಿಮಿಷಗಳ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    down: "ಸರ್ವರ್ ಸಂಪರ್ಕ ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಬ್ಯಾಕೆಂಡ್ ಚಾಲನೆಯಲ್ಲಿದೆಯೇ ಪರಿಶೀಲಿಸಿ.",
    off: "ಈ ಸರ್ವರ್‌ನಲ್ಲಿ ಸೈನ್-ಇನ್ ಇನ್ನೂ ಸಿದ್ಧವಾಗಿಲ್ಲ.",
  },
};

const DEMO = [
  { id: ADMIN_ID, role: "admin" },
];

export default function LoginPage() {
  const router = useRouter();
  const { lang, toggleLang } = useLang();
  const { theme, toggleTheme } = useTheme();
  const kn = lang === "kn";
  const t = COPY[lang];

  const [badge, setBadge] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | verifying | granted
  const [error, setError] = useState("");
  const [timeStr, setTimeStr] = useState("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const day = String(now.getDate()).padStart(2, "0");
      const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
      const month = months[now.getMonth()];
      const year = now.getFullYear();
      const hrs = String(now.getHours()).padStart(2, "0");
      const mins = String(now.getMinutes()).padStart(2, "0");
      const secs = String(now.getSeconds()).padStart(2, "0");
      setTimeStr(`${day} ${month} ${year} · ${hrs}:${mins}:${secs}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    
    // Prefetch main routes to ensure the transition is instant
    router.prefetch("/hook");
    router.prefetch("/antar");
    router.prefetch("/approvals");
    
    return () => clearInterval(interval);
  }, [router]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (status !== "idle") return;
    if (!badge.trim() || !password.trim()) {
      setError(t.empty);
      return;
    }
    // The server checks the password and answers the same way for a wrong password and
    // an unknown ID, so this page cannot be used to find out which IDs exist.
    setError("");
    setStatus("verifying");
    let acct;
    try {
      acct = await signIn(badge, password);
    } catch (err) {
      setStatus("idle");
      setPassword("");
      setError(err.status === 429 ? t.locked : err.status === 0 ? t.down : err.status === 503 ? t.off : t.bad);
      return;
    }
    // "Access granted" shows for a moment, then one curtain covers the change of screen.
    // It lives on <body>, so it is still there while this page is replaced, and the screen
    // that arrives lowers it once it has drawn (lib/curtain.js). The two timed waits and
    // the page's own overlay used to leave a flash of bare background between screens.
    setStatus("granted");
    await new Promise((r) => setTimeout(r, 220));
    raiseCurtain();
    await new Promise((r) => setTimeout(r, 260));     // the curtain's own fade, before the page under it changes

    // User logs in -> directed to /antar
    try {
      let loginCount = parseInt(localStorage.getItem("antar_login_count") || "0", 10);
      loginCount += 1;
      
      if (loginCount >= 7) {
        localStorage.removeItem("antar_docs_seen");
        loginCount = 0;
      }
      localStorage.setItem("antar_login_count", loginCount.toString());
    } catch {}
    
    const hookSeen = typeof window !== "undefined" && localStorage.getItem("antar_hook_seen");
    if (!hookSeen && acct.role !== "Approver") {
      router.push("/hook");
    } else {
      router.push(homeFor(acct.role));
    }
  }

  const busy = status !== "idle";

  return (
    <main className="lg-gate" style={{ position: "relative" }}>
      {/* Live Date & Time on Outer Screen (Top Right Corner) */}
      <div style={{
        position: "absolute",
        top: "24px",
        right: "32px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: "11px",
        color: "rgba(255,255,255,0.45)",
        letterSpacing: "0.05em",
        zIndex: 20
      }}>
        {timeStr}
      </div>

      <section className={`lg-card ${busy ? "busy" : ""}`}>

        <div className="lg-brandrow" style={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "flex-start", gap: "14px", marginBottom: "6px" }}>
          <img src={asset("/brand/antar_final_logo.png")} alt="Antar Icon" className="lg-brand-main-img" style={{ height: "52px", width: "52px", objectFit: "contain", filter: "drop-shadow(0 0 14px rgba(34,230,240,0.35))" }} />
          <span className="lg-wordmark">Antar</span>
        </div>
        <div className={`lg-tagline ${kn ? "kn" : ""}`}>{t.tag}</div>

        <form onSubmit={handleSubmit}>
          <div className="lg-field">
            <label htmlFor="badge" className={kn ? "kn" : ""}>{t.badge}</label>
            <div className="lg-input">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="1.8"><rect x="3" y="5" width="18" height="14" rx="2" /><circle cx="9" cy="11" r="2.4" /><path d="M14 10h4M14 14h4M6 16c.6-1.6 4.4-1.6 5 0" strokeLinecap="round" /></svg>
              <input id="badge" value={badge} onChange={(e) => setBadge(e.target.value)} placeholder="U-0001"
                     autoComplete="username" autoFocus disabled={busy} />
            </div>
          </div>
          <div className="lg-field">
            <label htmlFor="pw" className={kn ? "kn" : ""}>{t.pw}</label>
            <div className="lg-input">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="1.8"><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 1 1 8 0v3" /></svg>
              <input id="pw" type={showPw ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)}
                     placeholder={kn ? "ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ" : "Type your password"} autoComplete="current-password" disabled={busy} />
              <button type="button" className="lg-eye" aria-label={showPw ? "Hide password" : "Show password"} aria-pressed={showPw}
                      onClick={() => setShowPw((v) => !v)} disabled={busy}>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12z" /><circle cx="12" cy="12" r="2.6" /></svg>
              </button>
            </div>
          </div>

          <div className="lg-errline" role="alert" aria-live="polite">{error}</div>

          <button className={`lg-btn ${status}`} type="submit" aria-busy={status === "verifying"} disabled={busy && status !== "idle" ? true : false}>
            {status === "granted" ? (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
            ) : (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 1 1 8 0v3" /></svg>
            )}
            <span>{status === "verifying" ? t.verifying : status === "granted" ? t.granted : t.auth}</span>
          </button>

          <div className="lg-pulsewrap" style={{ opacity: status === "verifying" ? 1 : 0 }}>
            <div className="signal-pulse" />
          </div>
        </form>

        <div style={{ marginTop: "24px", textAlign: "center", display: "flex", justifyContent: "center", gap: "18px" }}>
          {/* The supervising officer signs in on the Approvals page (Account > Approvals). */}
          <button
            type="button"
            onClick={() => {
              setBadge(ADMIN_ID);
              // Filled only when this build was given a demo password (.env.local); otherwise the officer types it.
              setPassword(process.env.NEXT_PUBLIC_DEMO_PW_ADMIN || "");
              if (!process.env.NEXT_PUBLIC_DEMO_PW_ADMIN) document.getElementById("pw")?.focus();
              setError("");
            }}
            disabled={busy}
            style={{
              background: "transparent",
              border: "none",
              color: "rgba(255,255,255,0.35)",
              fontSize: "11px",
              fontFamily: "'JetBrains Mono', monospace",
              cursor: "pointer",
              letterSpacing: "0.06em",
              transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease"
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#22E6F0")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(255,255,255,0.35)")}
          >
            [ {kn ? "ಡೆಮೊ ಪ್ರವೇಶ" : "DEMO ACCESS"} ]
          </button>
        </div>
      </section>

      {/* Loading Animation Overlay for Chat Interface */}
      <div 
        style={{
          position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(3,5,12,0.92)",
          backdropFilter: "blur(8px)",
          zIndex: 9999,
          display: status === "loading_chat" ? "flex" : "none",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "32px",
          opacity: status === "loading_chat" ? 1 : 0,
          transition: "opacity 0.4s ease"
        }}
      >
        <div style={{ width: "240px", height: "2px", background: "rgba(34,230,240,0.1)", borderRadius: "2px", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", top: 0, left: 0, bottom: 0, width: "40%", background: "#94A3B8", boxShadow: "0 0 8px #94A3B8", borderRadius: "2px", animation: "grayLineSweep 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite" }}></div>
        </div>
        
      </div>

    </main>
  );
}
