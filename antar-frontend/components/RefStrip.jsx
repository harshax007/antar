"use client";

// Reference-design primitives shared by every screen (Task 02+):
// the same visual language the chat answer card uses - K/D/I/U badge,
// headline, stat chips, and a click-to-expand section for secondary detail.
// Styling comes from the global cx-* classes so all screens stay consistent.

import { useState } from "react";

const BADGE = {
  K: { cls: "cx-badge-k", label: "From the records" },
  D: { cls: "cx-badge-d", label: "D · Derived" },
  I: { cls: "cx-badge-i", label: "I · Inferred" },
  U: { cls: "cx-badge-u", label: "U · Lead" },
};

export function RefBadge({ tag = "K", label }) {
  const b = BADGE[tag] || BADGE.K;
  return <span className={b.cls}>{label || b.label}</span>;
}

export function RefChips({ chips }) {
  const items = (chips || []).filter((c) => c && c.value !== null && c.value !== undefined && c.value !== "");
  if (!items.length) return null;
  return (
    <div className="cx-statrow" style={{ marginTop: 0 }}>
      {items.map((c, i) => (
        <span className="cx-statchip" key={i} style={{ animationDelay: `${i * 70}ms` }}>
          <b>{String(c.value)}</b><i>{c.label}</i>
        </span>
      ))}
    </div>
  );
}

export function RefCollapse({ title, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="cx-collapse">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span>{title}</span>
        <span className="chev">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="cx-collapse-body">{children}</div>}
    </div>
  );
}

// The screen-level strip: [badge] headline · stat chips · optional collapse.
// Chips must carry REAL values (pass null/undefined to omit a chip - never a
// made-up number). `detail` renders inside the collapse when provided.
export default function RefStrip({ tag = "K", badgeLabel, title, chips, detailTitle, detail, style }) {
  return (
    <div style={{
      background: "rgba(14,24,46,0.82)", border: "1px solid rgba(255,255,255,0.09)",
      borderRadius: "14px", padding: "12px 16px", display: "flex", flexDirection: "column",
      gap: "9px", boxShadow: "0 8px 30px rgba(0,0,0,0.3)", ...style,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
        <RefBadge tag={tag} label={badgeLabel} />
        <span style={{ fontSize: "13.5px", fontWeight: 700, color: "var(--text, #F8FAFC)", lineHeight: 1.4 }}>
          {title}
        </span>
      </div>
      <RefChips chips={chips} />
      {detail && (
        <RefCollapse title={detailTitle || "Details"}>
          {detail}
        </RefCollapse>
      )}
    </div>
  );
}
