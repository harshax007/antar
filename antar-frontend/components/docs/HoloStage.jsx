"use client";

// The "nice simple 3D animation" (reference: holographic projector) - pure CSS
// 3D transforms, no three.js. Base slab + breathing light beam + a floating
// lucide icon rotating in 3D. Accent color + icon swap per demo stage.

import { Brain, Share2, Radar, Sparkles } from "lucide-react";

const ICONS = { think: Brain, connect: Share2, anticipate: Radar, wrap: Sparkles };

export default function HoloStage({ stage = "think", accent = "#22E6F0", label = "" }) {
  const Icon = ICONS[stage] || Sparkles;
  return (
    <div className="dmo-holo" style={{ "--acc": accent }} aria-hidden="true">
      <div className="dmo-holo-scene">
        <div className="dmo-holo-icon"><Icon size={54} strokeWidth={1.4} /></div>
        <div className="dmo-holo-beam" />
        <div className="dmo-holo-base">
          <span className="led" /><span className="led" /><span className="led" />
          <span className="dmo-holo-lbl">{label}</span>
        </div>
      </div>
    </div>
  );
}
