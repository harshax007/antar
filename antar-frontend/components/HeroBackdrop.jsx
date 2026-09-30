"use client";
import { useEffect, useState } from "react";
import { asset } from "@/lib/assets";

export default function HeroBackdrop() {
  const [shouldPlay, setShouldPlay] = useState(true);

  useEffect(() => {
    const conn = typeof navigator !== "undefined" ? navigator.connection : null;
    const isSaveData = conn && (conn.saveData || /(^|-)(2|3)g$/.test(conn.effectiveType || ""));
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    
    if (isSaveData || prefersReducedMotion) {
      setShouldPlay(false);
    }
  }, []);

  return (
    <div className="fx-backdrop" aria-hidden="true">
      {shouldPlay && (
        <video
          className="fx-video fx-video-on"
          src={asset("/brand/video/loading.mp4")}
          autoPlay
          muted
          loop
          playsInline
        />
      )}
      <svg className="fx-glow" viewBox="0 0 1200 700" preserveAspectRatio="xMidYMin slice">
        <defs>
          <filter id="fxBlur" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="25" />
          </filter>
          <radialGradient id="fxHue" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#22E6F0" stopOpacity=".16" />
            <stop offset="55%" stopColor="#0b3f46" stopOpacity=".10" />
            <stop offset="100%" stopColor="#060910" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx="600" cy="170" rx="430" ry="130" fill="url(#fxHue)" filter="url(#fxBlur)" />
      </svg>
      <i className="fx-line l25" /><i className="fx-line l50" /><i className="fx-line l75" />
      <div className="fx-grad-left" />
      <div className="fx-grad-bottom" />
    </div>
  );
}
