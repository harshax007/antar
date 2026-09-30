"use client";
import { useTheme, useLang } from "./Providers";
import { BRAND } from "@/lib/brand";
import { usePathname } from "next/navigation";
import AlertsDrawer from "./AlertsDrawer";
import { asset } from "@/lib/assets";

export default function HeaderStrip() {
  const { theme, toggleTheme } = useTheme();
  const { lang, toggleLang } = useLang();
  const pathname = usePathname();

  const titles = {
    "/ask": "Ask",
    "/map": "Map",
    "/predict": "Predict",
    "/profiles": "Quick Search",
    "/admin": "Account",
    "/network": "Brain"
  };
  const title = titles[pathname] || "";

  return (
    <header className="header-strip glass">
      <div className="left">
        <div className="brand" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <img src={asset("/brand/antar_final_logo.png")} alt="Antar Icon" className="lg-brand-main-img" style={{ height: "28px", width: "28px", objectFit: "contain", filter: "drop-shadow(0 0 8px rgba(34,230,240,0.3))" }} />
          <span className="logo" style={{ fontFamily: "'Chakra Petch'", fontWeight: 700, fontSize: "18px", letterSpacing: "0.08em", textTransform: "uppercase" }}>{BRAND.name}</span>
        </div>
        {title && <span className="page-title">{title}</span>}
      </div>
      <div className="right" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <AlertsDrawer />
        <label className="deep-search">
          <input type="checkbox" /> DeepSearch
        </label>
        <button className="toggle-btn" onClick={toggleTheme}>
          {theme === "dark" ? "Light" : "Dark"}
        </button>
        <button className="toggle-btn" onClick={toggleLang}>
          {lang === "en" ? "ಕನ್ನಡ" : "EN"}
        </button>
      </div>
    </header>
  );
}

