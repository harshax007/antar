"use client";

import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext();

// All screens are permanently locked to Dark Mode for consistent cinematic executive aesthetic
export function ThemeProvider({ children }) {
  const [theme] = useState("dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "dark");
    try { localStorage.removeItem("antar-theme"); } catch {}
  }, []);

  const toggleTheme = () => {};

  return (
    <ThemeContext.Provider value={{ theme: "dark", toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);

const LangContext = createContext();

export function LangProvider({ children }) {
  const [lang, setLang] = useState("en");

  const toggleLang = () => {
    setLang(lang === "en" ? "kn" : "en");
  };

  return (
    <LangContext.Provider value={{ lang, toggleLang }}>
      <div className={lang === "kn" ? "kn" : ""}>
        {children}
      </div>
    </LangContext.Provider>
  );
}

export const useLang = () => useContext(LangContext);
