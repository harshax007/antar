"use client";

import { useLang } from "@/components/Providers";

// EN | ಕನ್ನಡ, in the top nav on every screen (the chat's switch, shared). The language is
// the app's one setting (Providers), so flipping it here changes every screen.
export default function LangToggle() {
  const { lang, toggleLang } = useLang();
  const kn = lang === "kn";
  return (
    <button type="button" className="cx-lang" onClick={toggleLang}
            title={kn ? "ಇಂಗ್ಲಿಷ್‌ಗೆ ಬದಲಾಯಿಸಿ" : "Switch to Kannada"}
            aria-label={kn ? "ಭಾಷೆ: ಕನ್ನಡ. ಇಂಗ್ಲಿಷ್‌ಗೆ ಬದಲಾಯಿಸಿ" : "Language: English. Switch to Kannada"}>
      <span style={{ opacity: kn ? 0.5 : 1 }}>EN</span>
      <span style={{ opacity: 0.3 }}>|</span>
      <span style={{ opacity: kn ? 1 : 0.5, fontFamily: "'Noto Sans Kannada', sans-serif" }}>ಕನ್ನಡ</span>
    </button>
  );
}
