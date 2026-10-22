"use client";
import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { parseCSV, fromRecords, prepare } from "@/lib/crimeGraph";
import { getBrainCache, setBrainCache } from "@/lib/brainCache";
import { fetchAPI } from "@/lib/api";
const DataOverview = dynamic(() => import("@/components/DataOverview"), { ssr: false });
import { useLang } from "@/components/Providers";
import { asset } from "@/lib/assets";
import { motion, AnimatePresence } from "framer-motion";
import BrainLoader from "@/components/BrainLoader";

// 3d-force-graph touches `window` → client-only
const BrainStructure = dynamic(() => import("@/components/BrainStructure"), {
  ssr: false,
  loading: () => <BrainLoader />,
});
const CaseBrain = dynamic(() => import("@/components/CaseBrain"), { ssr: false });

// Screen 03 (served at /brain and /brain/structure): Page 01 (3D Brain Globe,
// mockup screen2_1_brain_structure) + scroll-down Page 02 (Data Overview).
// One shared selection {year, month, day, district, cats} keeps them synced.
// A suspect-id KPI (?kpi=S0001) renders the small case/profile view instead.
export default function BrainHub() {
  const sp = useSearchParams();
  const { lang } = useLang();
  const kn = lang === "kn";
  const kpi = (sp.get("suspect") || sp.get("kpi") || "").trim();
  const [recs, setRecs] = useState(null);
  const [sel, setSel] = useState({ year: null, month: null, day: null, district: null, cats: null });
  // Loading gate: hold the branded loader over the whole brain screen until the graph
  // data has actually arrived AND had a beat to build/paint - so the officer never
  // lands on an empty shell mid-load. (owner req: wait for complete load.)
  const [contentReady, setContentReady] = useState(false);
  const topRef = useRef(null);
  const isCase = /^S\d+/i.test(kpi);

  useEffect(() => {
    if (isCase) return;
    let alive = true;

    // Intelligent Data (the constellation) = the curated, densely-linked world from
    // intelligent.db (3,500 rows) served by /api/dataset/graph. Falls back to the
    // bundled fir_synthetic.csv if the API is unreachable (e.g. static-only deploy).
    getBrainCache().then((cached) => {
      if (cached && alive) setRecs(prepare(cached));

      fetchAPI("/api/dataset/graph?limit=3500")
        .then((d) => {
          if (!d?.rows) return;
          const recsRaw = fromRecords(d.rows);
          setBrainCache(recsRaw);
          if (alive) setRecs(prepare(recsRaw));
        })
        .catch(() => {
          if (cached) return;
          fetch(asset("/fir_synthetic.csv"))
            .then((r) => { if (!r.ok) throw new Error("csv"); return r.text(); })
            .then((t) => {
              const recsRaw = parseCSV(t);
              setBrainCache(recsRaw);
              if (alive) setRecs(prepare(recsRaw));
            })
            .catch(() => { if (alive) setRecs([]); });
        });
    });
    return () => { alive = false; };
  }, [isCase]);

  // Reveal the screen only once records exist and the constellation has had two paint
  // frames + a short settle to build its first layout. Until then the loader stays up.
  useEffect(() => {
    if (isCase) return;
    if (recs === null) { setContentReady(false); return; }
    let raf1 = 0, raf2 = 0, timer = 0;
    raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        timer = setTimeout(() => setContentReady(true), 700);
      });
    });
    return () => { cancelAnimationFrame(raf1); cancelAnimationFrame(raf2); clearTimeout(timer); };
  }, [recs, isCase]);

  if (isCase) return <CaseBrain suspectId={kpi.toUpperCase()} />;

  const smoothScrollTo = (container, targetY, duration) => {
    const startY = container.scrollTop;
    const difference = targetY - startY;
    const startTime = performance.now();

    const step = (currentTime) => {
      let progress = (currentTime - startTime) / duration;
      if (progress > 1) progress = 1;
      
      // Industry standard easeInOutQuart
      const ease = progress < 0.5
        ? 8 * progress * progress * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 4) / 2;

      container.scrollTop = startY + (difference * ease);

      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  };

  const scrollToSection = (which) => {
    const container = document.querySelector(".ax-main") || document.documentElement;
    if (!container) return;
    
    if (which === "top") {
      smoothScrollTo(container, 0, 800); // 800ms duration
      return;
    }
    
    const target = document.getElementById("data-overview");
    if (!target) return;
    
    const cRect = container.getBoundingClientRect();
    const tRect = target.getBoundingClientRect();
    
    // Calculate precise target Y coordinate inside the scroll container
    const maxScroll = container.scrollHeight - container.clientHeight;
    let targetTop = container.scrollTop + (tRect.top - cRect.top);
    if (targetTop > maxScroll) targetTop = maxScroll; // Clamp to max
    
    smoothScrollTo(container, targetTop, 800);
  };
  const jumpTop = (go) => { if (go) scrollToSection("top"); };

  return (
    <div className="bsx-wrap" style={{ scrollBehavior: "smooth" }}>
      <div ref={topRef} style={{ position: "relative", minHeight: "calc(100vh - 64px)", display: "flex", flexDirection: "column" }}>

        <div style={{ flex: 1, position: "relative" }}>
          <BrainStructure focusId={kpi} recs={recs} sel={sel} setSel={setSel} />
        </div>
        {!(sel.type === "node" || sel.type === "group") && (
          <div style={{ position: "fixed", bottom: "64px", right: "20px", zIndex: 10, display: "flex", flexDirection: "column", gap: "12px", alignItems: "flex-end" }}>
            <button
              onClick={() => scrollToSection("top")}
              title="Scroll to Top"
              style={{ background: "transparent", border: "none", color: "#FFFFFF", textShadow: "0 0 10px rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", transition: "color 0.25s ease, background-color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease, transform 0.25s ease, scale 0.25s ease", fontFamily: "'Chakra Petch', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }}
              onMouseOver={(e) => { e.currentTarget.style.textShadow = "0 0 16px rgba(255,255,255,0.8)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
              onMouseOut={(e) => { e.currentTarget.style.textShadow = "0 0 10px rgba(255,255,255,0.4)"; e.currentTarget.style.transform = "translateY(0)"; }}
            >
              Top Brain
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 15l-6-6-6 6" /></svg>
            </button>
            <button
              onClick={() => scrollToSection("bottom")}
              title="Scroll to Data Overview"
              style={{ background: "transparent", border: "none", color: "#FFFFFF", textShadow: "0 0 10px rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", transition: "color 0.25s ease, background-color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease, transform 0.25s ease, scale 0.25s ease", fontFamily: "'Chakra Petch', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }}
              onMouseOver={(e) => { e.currentTarget.style.textShadow = "0 0 16px rgba(255,255,255,0.8)"; e.currentTarget.style.transform = "translateY(2px)"; }}
              onMouseOut={(e) => { e.currentTarget.style.textShadow = "0 0 10px rgba(255,255,255,0.4)"; e.currentTarget.style.transform = "translateY(0)"; }}
            >
              Bottom Data Overview
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>
            </button>
          </div>
        )}
      </div>
      <DataOverview recs={recs} sel={sel} setSel={setSel} onJumpTop={jumpTop} />
    </div>
  );
}
