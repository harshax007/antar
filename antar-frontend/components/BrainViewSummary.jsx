"use client";

import { useMemo, useState } from "react";
import { aliasFor } from "@/lib/crimeGraph";

// "View summary" - the brain view, in sentences an officer can read aloud.
//
// Everything here is computed from what is on screen right now: the graph the brain is
// drawing, the filters and the focused group. Nothing is generated and nothing is
// fetched; the panel only opens when clicked. Sentences name numbers and people exactly
// as the graph holds them, so the summary can never disagree with the picture.

const LINK_WORDS = {
  repeat: ["the same accused", "ಅದೇ ಆರೋಪಿ"],
  ring: ["a place or vehicle", "ಹಂಚಿಕೆಯ ಸ್ಥಳ ಅಥವಾ ವಾಹನ"],
  cyber: ["a UPI id or IP address", "ಹಂಚಿಕೆಯ UPI ಅಥವಾ IP"],
  inferred: ["a predicted MO match", "ಊಹಿತ MO ಹೊಂದಾಣಿಕೆ"],
  unsub: ["an unidentified-suspect cluster", "ಅಪರಿಚಿತ ಶಂಕಿತ ಗುಂಪು"],
};

function listJoin(items, kn) {
  const a = items.filter(Boolean);
  if (a.length <= 1) return a[0] || "";
  return `${a.slice(0, -1).join(", ")} ${kn ? "ಮತ್ತು" : "and"} ${a[a.length - 1]}`;
}

// The collapsible "View summary" shell every Brain screen uses - All Data, Focus, Crime
// Graph and the 02 Data Overview - so each reads and behaves the same: closed until
// clicked, sentences built from what is on screen, recomputed whenever the view changes.
// A line is either a sentence (focus mode, where the prose IS the point) or a
// [label, value] pair. Pairs render as a compact two-column list: the officer scans the
// left column and stops at the row they need, instead of reading four sentences to find
// one number.
function Line({ line }) {
  if (Array.isArray(line)) {
    return (
      <div className="bsx-sumrow">
        <span className="k">{line[0]}</span>
        <span className="v">{line[1]}</span>
      </div>
    );
  }
  return <p>{line}</p>;
}


// `always` turns the panel from a disclosure into a description: no button, no chevron,
// always on screen. It reads grey at rest and comes up to full contrast on hover, so it
// is available without ever being in the way. The Data Overview keeps the click-to-open
// form, where the page is a document and a permanently open block would crowd it.
export function SummaryToggle({ lines, kn, footer, className = "", title, always = false }) {
  const [open, setOpen] = useState(false);
  if (always) {
    return (
      <div className={`bsx-summary always ${className}`}>
        <div className="bsx-summary-h as-title">
          {title || (kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "View Summary")}
        </div>
        <div className="bsx-summary-b" role="region" aria-live="polite">
          {!lines?.length
            ? <p>{kn ? "ಮಾಹಿತಿ ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Still loading…"}</p>
            : lines.map((ln, i) => <Line key={i} line={ln} />)}
          <div className="bsx-summary-k">{footer || (kn ? "ತೆರೆಯ ಮೇಲಿನ ದಾಖಲೆಗಳಿಂದ" : "computed from the records on screen")}</div>
        </div>
      </div>
    );
  }
  return (
    // Recedes to a hint until pointed at or opened, so it stops competing with the brain
    // for attention while staying exactly where the officer last saw it. Hover, keyboard
    // focus and the open state all bring it back to full strength.
    <div className={`bsx-summary ${open ? "open" : ""} ${className}`}>
      <button className="bsx-summary-h" aria-expanded={open} onClick={() => setOpen(!open)}>
        {title || (kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "View summary")}
        <span aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <div className="bsx-summary-b" role="region" aria-live="polite">
          {!lines?.length
            ? <p>{kn ? "ಮಾಹಿತಿ ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Still loading…"}</p>
            : lines.map((ln, i) => <Line key={i} line={ln} />)}
          <div className="bsx-summary-k">{footer || (kn ? "ತೆರೆಯ ಮೇಲಿನ ದಾಖಲೆಗಳಿಂದ" : "computed from the records on screen")}</div>
        </div>
      )}
    </div>
  );
}

export default function BrainViewSummary({ graph, stats, focus, active, kinds, groupBy, scope, district, dim3d, kn, always = false }) {
  const [open, setOpen] = useState(false);

  // What this panel is a summary OF. Each view answers a different question, so the
  // heading and the opening line name that question rather than repeating "View summary"
  // over four different pictures.
  const title = kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "View Summary";

  const lines = useMemo(() => {
    if (!graph) return [];
    const out = [];
    // Lead with what is on screen and why it is arranged that way. Without it the panel
    // opened straight into numbers, and the officer had to infer which view produced them.
    const showing = focus?.meta?.kind === "cat"
      ? (kn
          ? `ಈ ವೀಕ್ಷಣೆಯ ${focus.comp?.size || 0} ${focus.meta.label} FIR ಗಳು ಮಾತ್ರ.`
          : `Every ${focus.meta.label} FIR in this view - ${focus.comp?.size || 0} of them - pulled out of the ball together.`)
      : focus
        ? (kn
            ? "ಒಂದೇ ಸಾಕ್ಷ್ಯದಿಂದ ಜೋಡಿದ ಒಂದು ಗುಂಪು."
            : "One group of FIRs that are tied together by shared evidence.")
        : groupBy === "evidence"
          ? (kn
              ? "ಹಂಚಿದ ಸಾಕ್ಷ್ಯದ ಮೂಲಕ ಜೋಡಣೆ: ಒಂದೇ ಆರೋಪಿ, ವಾಹನ, UPI ಅಥವಾ IP."
              : "Grouped by what the records share - the same accused, vehicle, UPI id or IP. Clusters here are cases that may belong together.")
          : (kn
              ? "ಅಪರಾಧ ಪ್ರಕಾರದ ಮೂಲಕ ಜೋಡಣೆ; ಪ್ರತಿ ಬ್ಲಾಬ್ ಒಂದು ಪ್ರಕಾರ."
              : "Grouped by crime type - each blob is one category, sized by how many FIRs it holds.");
    out.push(showing);
    const firs = (graph.nodes || []).filter((n) => n.kind === "fir");
    const linked = firs.filter((n) => n.linked).length;
    const isolated = firs.length - linked;
    const cats = (graph.categories || []).filter((c) => active === null || active?.has?.(c.cat));
    const total = cats.reduce((s, c) => s + (c.count || 0), 0);
    const top = [...cats].sort((a, b) => (b.count || 0) - (a.count || 0))[0];

    if (focus) {
      // Focused group: say WHO is connected, HOW, and WHERE - the question an officer is
      // actually asking when they click a node.
      const people = (focus.comp?.people || []).map((p) => p.name || aliasFor(p.id)).slice(0, 4);
      const whys = (focus.whys || []).map((w) => w.text).slice(0, 3);
      const dists = focus.comp?.districts || [];
      const yrs = focus.comp?.years;

      // Focus stays as sentences on purpose: here the officer wants the story of one
      // group — who, how, where — and a fact table would strip exactly the connective
      // words that make it a lead rather than a list.
      out.push([kn ? "ಗುಂಪು" : "Group",
                kn ? `${focus.comp?.size || 0} FIR · ${dists.length} ಜಿಲ್ಲೆ${yrs ? ` · ${yrs[0]}-${yrs[1]}` : ""}`
                   : `${focus.comp?.size || 0} FIRs · ${dists.length} district${dists.length === 1 ? "" : "s"}${yrs ? ` · ${yrs[0]}-${yrs[1]}` : ""}`]);
      if (people.length) {
        out.push([kn ? "ಜನರು" : "People", listJoin(people, kn)]);
      }
      if (whys.length) {
        out.push([kn ? "ಏಕೆ ಜೋಡಣೆ" : "Linked by", whys.join(" · ")]);
      }
      if (dists.length) {
        out.push([kn ? "ಜಿಲ್ಲೆಗಳು" : "Districts", listJoin(dists.slice(0, 5), kn)]);
      }
      const mainCat = focus.comp?.cats?.[0];
      if (mainCat) {
        out.push([kn ? "ಹೆಚ್ಚಿನವು" : "Mostly",
                  `${mainCat.label} (${mainCat.n}/${focus.comp.size})`]);
      }
      out.push(kn ? "ಇದು ದಾಖಲೆಗಳಿಂದ ಬಂದ ಸಂಪರ್ಕ; ಅಪರಾಧದ ಪುರಾವೆ ಅಲ್ಲ - ತನಿಖೆಯ ಸುಳಿವು."
                  : "These are record links, not proof of guilt - a lead to investigate.");
      return out;
    }

    // Scannable facts, not paragraphs. The old version opened with a 30-word sentence
    // restating the filter bar directly above it, then buried the two numbers an officer
    // actually wants: how much of this is connected, and who to look at first.
    out.push([kn ? "ವೀಕ್ಷಣೆ" : "View",
              `${firs.length.toLocaleString()} FIRs · `
              + `${String(scope).replace(/^All years/, "all years")}`
              + (district ? ` · ${district}` : "")]);
    out.push([kn ? "ಗುಂಪು" : "Grouped by",
              (groupBy === "evidence"
                ? (kn ? "ಹಂಚಿದ ಸಾಕ್ಷ್ಯ" : "shared evidence")
                : (kn ? "ಅಪರಾಧ ಪ್ರಕಾರ" : "crime type")) + ` · ${dim3d ? "3D" : "2D"}`]);

    if (firs.length) {
      out.push([kn ? "ಸಂಪರ್ಕಿತ" : "Connected",
                kn ? `${linked.toLocaleString()} ಸಂಪರ್ಕಿತ · ${isolated.toLocaleString()} ಒಂಟಿ`
                   : `${linked.toLocaleString()} linked · ${isolated.toLocaleString()} isolated`]);
    }

    const byKind = [["repeat", stats?.repeat], ["ring", stats?.ring], ["cyber", stats?.cyber]]
      .filter(([k, n]) => n > 0 && kinds?.has?.(k));
    if (byKind.length) {
      // stats count linked GROUPS (a star of FIRs around one shared key), not lines.
      out.push([kn ? "ಕೊಂಡಿಗಳು" : "Link types",
                byKind.map(([k, n]) => `${n.toLocaleString()} ${LINK_WORDS[k][kn ? 1 : 0]}`)
                      .join(" · ")]);
    }

    if (top && total) {
      out.push([kn ? "ದೊಡ್ಡ ಗುಂಪು" : "Largest",
                `${top.label} — ${(top.count || 0).toLocaleString()}`
                + ` (${Math.round((100 * (top.count || 0)) / total)}%)`]);
    }

    // The most connected accused on screen — the first person worth a closer look, and
    // the reason this panel is worth opening at all.
    const deg = new Map();
    (graph.links || []).forEach((l) => {
      if (l.kind !== "repeat") return;
      [l.source, l.target].forEach((end) => {
        const id = typeof end === "object" ? end.id : end;
        deg.set(id, (deg.get(id) || 0) + 1);
      });
    });
    const hubId = [...deg.entries()].sort((a, b) => b[1] - a[1])[0];
    const hub = hubId ? firs.find((n) => n.id === hubId[0]) : null;
    if (hub?.accused) {
      out.push([kn ? "ಗಮನಿಸಿ" : "Look first",
                `${aliasFor(hub.accused)} (${hub.accused})`]);
    }

    const hiddenCats = active === null ? 0 : (graph.categories || []).length - cats.length;
    if (hiddenCats > 0) {
      out.push([kn ? "ಮರೆಮಾಡಲಾಗಿದೆ" : "Hidden",
                kn ? `${hiddenCats} ಅಪರಾಧ ಪ್ರಕಾರ` : `${hiddenCats} crime type${hiddenCats === 1 ? "" : "s"}`]);
    }
    return out;
  }, [graph, stats, focus, active, kinds, groupBy, scope, district, dim3d, kn]);

  return <SummaryToggle lines={lines} kn={kn} title={title} always={always}
                        footer={kn ? "K · ತೆರೆಯ ಮೇಲಿನ ದಾಖಲೆಗಳಿಂದ" : "K · computed from the records on screen"} />;
}
