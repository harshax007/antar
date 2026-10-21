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

  // The choice is kept in this browser, so a reload or a link opened in a new tab stays in the
  // officer's language. Read after mount: the server renders English, and reading storage
  // during the first render would not match it.
  useEffect(() => {
    try { if (localStorage.getItem("antar_lang") === "kn") setLang("kn"); } catch {}
  }, []);
  useEffect(() => {
    try { document.documentElement.lang = lang === "kn" ? "kn" : "en"; } catch {}
  }, [lang]);

  const toggleLang = () => {
    const next = lang === "en" ? "kn" : "en";
    setLang(next);
    try { localStorage.setItem("antar_lang", next); } catch {}
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
