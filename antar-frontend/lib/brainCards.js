// Hover cards and link reasons for the Brain globes (2D Constellation and 3D), shared so
// both read the same, in English and Kannada. The graph libraries render tooltips from an
// HTML string, so these return markup; every value from the records is escaped.
import { aliasFor } from "@/lib/crimeGraph";
import { crimeKn, stageKn } from "@/lib/kn";

const esc = (v) => String(v ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Every drawn edge exists because two FIRs share a real key - name it.
const LINK_WHY = {
  repeat: ["Repeat offender: same accused", "ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿ: ಅದೇ ಆರೋಪಿ"],
  ring: ["Ring: shared place / vehicle", "ರಿಂಗ್: ಹಂಚಿದ ಸ್ಥಳ / ವಾಹನ"],
  cyber: ["Cyber: shared UPI / IP", "ಸೈಬರ್: ಹಂಚಿದ UPI / IP"],
  inferred: ["Predicted link (inferred, not in the record)", "ಊಹಿತ ಕೊಂಡಿ (ದಾಖಲೆಯಲ್ಲಿಲ್ಲ)"],
  unsub: ["Unsolved case in an unidentified-suspect group", "ಅಪರಿಚಿತ ಶಂಕಿತ ಗುಂಪಿನ ಪತ್ತೆಯಾಗದ ಪ್ರಕರಣ"],
  agent: ["Antar agent: runs its checks over this graph", "Antar ಏಜೆಂಟ್: ಈ ಗ್ರಾಫ್ ಮೇಲೆ ಪರಿಶೀಲನೆ ನಡೆಸುತ್ತದೆ"],
};

export function linkWhy(l, kn = false) {
  const [en, k] = LINK_WHY[l.kind] || ["Linked", "ಜೋಡಿತ"];
  const key = l.key && l.kind !== "agent" && l.kind !== "unsub" ? ` — ${l.key}` : "";
  return `${kn ? k : en}${key}`;
}

// The reasons holding a focused group together, deduplicated, in both languages.
export function groupWhys(links, members) {
  const whys = [], seen = new Set();
  links.forEach((l) => {
    const sid = typeof l.source === "object" ? l.source.id : l.source;
    const tid = typeof l.target === "object" ? l.target.id : l.target;
    if (!members.has(sid) || !members.has(tid)) return;
    const text = linkWhy(l);
    if (!seen.has(text)) { seen.add(text); whys.push({ kind: l.kind, text, text_kn: linkWhy(l, true) }); }
  });
  return whys;
}

// "UNSUB-03 · Burglary" -> "ಅಪರಿಚಿತ-03 · ಮನೆಗಳ್ಳತನ"
export function unsubName(n, kn = false) {
  const name = n.name || "UNSUB";
  if (!kn) return name;
  const crime = n.crimeGroup ? (crimeKn(n.crimeGroup) || n.crimeGroup) : "";
  const num = /UNSUB-(\d+)/.exec(name)?.[1];
  return num ? `ಅಪರಿಚಿತ-${num}${crime ? ` · ${crime}` : ""}` : `ಅಪರಿಚಿತ ಶಂಕಿತ${crime ? ` · ${crime}` : ""}`;
}

export function unsubCard(n, kn = false) {
  const what = kn
    ? "ಒಂದೇ ಪ್ರದೇಶದ, ಒಂದೇ ಬಗೆಯ 3 ಅಥವಾ ಹೆಚ್ಚು ಪತ್ತೆಯಾಗದ FIR ಗಳನ್ನು ಒಬ್ಬನೇ ಅಪರಿಚಿತ ಅಪರಾಧಿಯ ಸಾಧ್ಯತೆಯಾಗಿ ಗುಂಪು ಮಾಡಲಾಗಿದೆ."
    : "Three or more unsolved FIRs of the same kind in the same area, grouped as possibly one unknown offender.";
  const note = kn ? "ಪರಿಶೀಲಿಸಬೇಕಾದ ಊಹೆ, ಗೊತ್ತಿರುವ ವ್ಯಕ್ತಿಯಲ್ಲ." : "A guess to check, not a known person.";
  return `<div style="background:rgba(15,10,25,0.96); border:1px solid rgba(168,85,247,0.6); padding:12px 15px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.9); font:12px Inter, sans-serif; color:#E9D5FF; max-width:300px;"><b style="color:#C084FC; font-size:13px; font-family:'Chakra Petch', sans-serif;">${esc(unsubName(n, kn))}</b><div style="margin-top:6px; color:#D8B4FE; font-size:11px; line-height:1.4;">${what}</div><div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.1); font-size:11px; color:#CBD5E1;">${note}</div></div>`;
}

const ROLE_NOTE = {
  top: ["#34EEB6", "Most connected record in this view", "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ಸಂಪರ್ಕಿತ ದಾಖಲೆ"],
  hub: ["#FFC048", "Accused named in many linked FIRs here", "ಇಲ್ಲಿನ ಹಲವು ಜೋಡಿತ FIR ಗಳಲ್ಲಿ ಹೆಸರಿರುವ ಆರೋಪಿ"],
  comm: ["#22E6F0", "Part of a group linked by shared evidence", "ಹಂಚಿದ ಸಾಕ್ಷ್ಯದಿಂದ ಜೋಡಿತ ಗುಂಪಿನ ಭಾಗ"],
};

export function firCard(n, kn = false) {
  const crime = n.crimeHead || n.crimeGroup;
  const title = crime ? ((kn && (crimeKn(n.crimeHead) || crimeKn(n.crimeGroup))) || crime) : (kn ? "FIR ದಾಖಲೆ" : "FIR record");
  const stage = n.stage ? ((kn && stageKn(n.stage)) || n.stage) : "";
  const where = [n.zone, n.district && n.district !== n.zone ? n.district : null, n.year].filter(Boolean).join(" · ");
  const role = ROLE_NOTE[n.role] || (n.comm ? ROLE_NOTE.comm : null);
  const edge = n.role === "top" ? "rgba(24,214,154,0.6)" : n.role === "hub" ? "rgba(232,163,61,0.6)" : "rgba(43,179,163,0.4)";
  const head = n.role === "top" ? "#34EEB6" : n.role === "hub" ? "#FFC048" : "#22E6F0";
  return `<div style="background:rgba(6,11,18,0.96); border:1px solid ${edge}; padding:12px 15px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.9); font:12px Inter, sans-serif; color:#E2E8F0; max-width:300px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; gap:8px;">
        <b style="color:${head}; font-size:13px; font-family:'Chakra Petch', sans-serif;${kn ? "" : " text-transform:uppercase;"}">${esc(title)}</b>
        ${stage ? `<span style="font-size:10px; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; color:#A7F3D0; white-space:nowrap;">${esc(stage)}</span>` : ""}
      </div>
      ${where ? `<div style="color:#94A3B8; font-size:11px; margin-bottom:6px;">${esc(where)}</div>` : ""}
      ${n.accused ? `<div style="background:rgba(232,163,61,0.12); border-left:3px solid #E8A33D; padding:5px 8px; margin:6px 0; border-radius:0 4px 4px 0;"><span style="color:#FDE68A; font-weight:600;">${esc(aliasFor(n.accused) || (kn ? "ಆರೋಪಿ" : "Accused"))}</span> <span style="color:#94A3B8; font-family:'JetBrains Mono'; font-size:11px;">[${esc(n.accused)}]</span></div>` : ""}
      ${n.vehicle ? `<div style="color:#38BDF8; font-size:11px; margin-top:4px; font-family:'JetBrains Mono';">${kn ? "ವಾಹನ" : "Vehicle"}: <b>${esc(n.vehicle)}</b></div>` : ""}
      ${n.mo ? `<div style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1); font-size:11px; color:#CBD5E1; line-height:1.4;"><b>${kn ? "ಕೃತ್ಯದ ವಿಧಾನ (MO)" : "How it was done (MO)"}:</b><br/>${esc(n.mo)}</div>` : ""}
      ${role ? `<div style="margin-top:8px; font-size:11px; color:${role[0]}; font-weight:600;">${kn ? role[2] : role[1]}</div>` : ""}
    </div>`;
}

// Agent nodes: what the purple/teal dots are, and what clicking one does.
export function agentCard(n, kn = false) {
  const sub = kn ? "Antar ಏಜೆಂಟ್: ಈ ಗ್ರಾಫ್ ಮೇಲೆ ಪರಿಶೀಲನೆ ನಡೆಸುತ್ತದೆ" : "Antar agent: runs its checks over this graph";
  const cta = kn ? "ಇದು ಏನು ಪರಿಶೀಲಿಸಿತು ಎಂದು ನೋಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ" : "Click to see what it checked";
  return `<div style="background:rgba(10,15,24,0.96); border:1px solid rgba(167,139,250,0.45); padding:10px 14px; border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,0.85); font:12px 'Chakra Petch', Inter, sans-serif; color:#E2E8F0; max-width:300px;"><b style="color:#C4B5FD; font-size:13px; letter-spacing:0.5px;">${esc(n.label || "Antar")}</b><br/><span style="color:#94A3B8; font-size:11px;">${sub}</span><div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.1); color:#38BDF8; font-weight:600;">▶ ${cta}</div></div>`;
}

export const nodeCard = (n, kn = false) =>
  n.kind === "agent" ? agentCard(n, kn) : n.kind === "unsub" ? unsubCard(n, kn) : firCard(n, kn);

export const linkCard = (l, kn = false) =>
  `<div style="background:rgba(6,11,18,0.94); border:1px solid rgba(255,140,66,0.4); padding:5px 9px; border-radius:6px; font:11px 'JetBrains Mono', monospace; color:#FFB020; box-shadow:0 6px 16px rgba(0,0,0,0.85);">${esc(linkWhy(l, kn))}</div>`;
