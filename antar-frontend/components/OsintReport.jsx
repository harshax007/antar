"use client";

import { useState } from "react";

// What one OSINT run found, laid out the way an officer reads it: the summary first (what this
// is, what the open web shows, what was checked live, what to do next), then the detail behind
// each line. Everything here is an unverified lead; nothing is written to the FIR record.
// The screen's own words are in English and Kannada (T); the findings are as the server wrote them.

const T = {
  copySheet: ["Copy lead sheet", "ಸುಳಿವು ಪಟ್ಟಿ ನಕಲಿಸಿ"],
  copied: ["Copied", "ನಕಲಿಸಲಾಗಿದೆ"],
  whatItIs: ["What it is", "ಇದು ಏನು"],
  openWeb: ["Open web", "ಮುಕ್ತ ವೆಬ್"],
  notes: ["Points to note", "ಗಮನಿಸಬೇಕಾದವು"],
  next: ["What to do next", "ಮುಂದೆ ಏನು ಮಾಡಬೇಕು"],
  foot: ["Unverified open-source leads, not evidence. Nothing here is added to the FIR record.",
         "ಪರಿಶೀಲಿಸದ ಮುಕ್ತ-ಮೂಲ ಸುಳಿವುಗಳು, ಸಾಕ್ಷ್ಯವಲ್ಲ. ಇಲ್ಲಿನ ಯಾವುದೂ FIR ದಾಖಲೆಗೆ ಸೇರುವುದಿಲ್ಲ."],
  tPages: ["Open-web pages", "ವೆಬ್ ಪುಟಗಳು"],
  tLive: ["Checked live", "ನೇರ ಪರಿಶೀಲನೆ"],
  tOfficial: ["Official checks", "ಅಧಿಕೃತ ಪರಿಶೀಲನೆ"],
  tDetails: ["What it decodes to", "ಇದರ ವಿವರ"],
  tNotice: ["Notice to send", "ಕಳುಹಿಸಬೇಕಾದ ನೋಟಿಸ್"],
  tProfiles: ["Profile links", "ಪ್ರೊಫೈಲ್ ಲಿಂಕ್‌ಗಳು"],
  tLog: ["Step log", "ಹಂತಗಳ ದಾಖಲೆ"],
  unreached: ["The open-web search could not be reached just now. Run it again in a minute.",
              "ವೆಬ್ ಹುಡುಕಾಟ ಈಗ ತಲುಪಲಿಲ್ಲ. ಒಂದು ನಿಮಿಷದ ನಂತರ ಮತ್ತೆ ಚಲಾಯಿಸಿ."],
  checked: ["pages checked", "ಪುಟಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗಿದೆ"],
  contain: ["contain it", "ಇದನ್ನು ಹೊಂದಿವೆ"],
  dropped: ["did not and were left out", "ಹೊಂದಿಲ್ಲ, ಬಿಡಲಾಗಿದೆ"],
  searchedFor: ["Searched for:", "ಹುಡುಕಿದ್ದು:"],
  noPage: ["No public page mentions it. That is a result: nothing about this is on the open web that a search can find.",
           "ಯಾವುದೇ ಸಾರ್ವಜನಿಕ ಪುಟ ಇದನ್ನು ಉಲ್ಲೇಖಿಸಿಲ್ಲ. ಇದೂ ಒಂದು ಫಲಿತಾಂಶ: ಹುಡುಕಾಟಕ್ಕೆ ಸಿಗುವಂತೆ ಮುಕ್ತ ವೆಬ್‌ನಲ್ಲಿ ಇದರ ಬಗ್ಗೆ ಏನೂ ಇಲ್ಲ."],
  weightTip: ["How much weight this page deserves: an exact match counts more, and a court, government or news page more than an unknown site",
              "ಈ ಪುಟಕ್ಕೆ ಎಷ್ಟು ತೂಕ: ನಿಖರ ಹೊಂದಾಣಿಕೆ ಹೆಚ್ಚು; ನ್ಯಾಯಾಲಯ, ಸರ್ಕಾರಿ ಅಥವಾ ಸುದ್ದಿ ಪುಟ ಅಪರಿಚಿತ ತಾಣಕ್ಕಿಂತ ಹೆಚ್ಚು"],
  matched: ["Matched:", "ಹೊಂದಿದ್ದು:"],
  alsoMentions: ["Also mentions:", "ಇದನ್ನೂ ಉಲ್ಲೇಖಿಸುತ್ತದೆ:"],
  hashTip: ["Fingerprint of the page address and text as seen, for the record", "ದಾಖಲೆಗಾಗಿ ಪುಟದ ವಿಳಾಸ ಮತ್ತು ಪಠ್ಯದ ಗುರುತು"],
  liveNote: ["Answered just now by the public registry named on each card. Only the identifier was sent; nothing about the case.",
             "ಪ್ರತಿ ಕಾರ್ಡ್‌ನಲ್ಲಿರುವ ಸಾರ್ವಜನಿಕ ದಾಖಲೆಯಿಂದ ಈಗಷ್ಟೇ ಬಂದ ಉತ್ತರ. ಗುರುತು ಮಾತ್ರ ಕಳುಹಿಸಲಾಗಿದೆ; ಪ್ರಕರಣದ ಬಗ್ಗೆ ಏನೂ ಇಲ್ಲ."],
  source: ["Source:", "ಮೂಲ:"],
  open: ["open ↗", "ತೆರೆಯಿರಿ ↗"],
  openBtn: ["Open ↗", "ತೆರೆಯಿರಿ ↗"],
  offNote: ["Government and public portals to check this on. Open each in your own login; Antar does not sign in to them.",
            "ಇದನ್ನು ಪರಿಶೀಲಿಸಬೇಕಾದ ಸರ್ಕಾರಿ ಮತ್ತು ಸಾರ್ವಜನಿಕ ಪೋರ್ಟಲ್‌ಗಳು. ನಿಮ್ಮ ಸ್ವಂತ ಲಾಗಿನ್‌ನಲ್ಲಿ ತೆರೆಯಿರಿ; ಅಂತರ್ ಅವುಗಳಿಗೆ ಲಾಗಿನ್ ಆಗುವುದಿಲ್ಲ."],
  tellsYou: ["Tells you", "ತಿಳಿಸುವುದು"],
  how: ["How", "ಹೇಗೆ"],
  copyVal: ["Copy", "ನಕಲಿಸಿ"],
  toPaste: ["to paste", "ಅಂಟಿಸಲು"],
  detailsNote: ["Worked out from the identifier itself; nothing was looked up for this.",
                "ಗುರುತಿನಿಂದಲೇ ಲೆಕ್ಕಿಸಲಾಗಿದೆ; ಇದಕ್ಕಾಗಿ ಏನನ್ನೂ ಹುಡುಕಿಲ್ಲ."],
  to: ["To:", "ಗೆ:"],
  subject: ["Subject:", "ವಿಷಯ:"],
  copyNotice: ["Copy notice", "ನೋಟಿಸ್ ನಕಲಿಸಿ"],
  noticeNote: ["A draft. Check the facts, add the case reference, and send it under the signature of the officer authorised to issue it.",
               "ಇದು ಕರಡು. ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ, ಪ್ರಕರಣ ಸಂಖ್ಯೆ ಸೇರಿಸಿ, ಅಧಿಕೃತ ಅಧಿಕಾರಿಯ ಸಹಿಯೊಂದಿಗೆ ಕಳುಹಿಸಿ."],
  profNote: ["Public profile pages to open by hand. None was opened here, so none is a finding until you have looked.",
             "ಕೈಯಾರೆ ತೆರೆಯಬೇಕಾದ ಸಾರ್ವಜನಿಕ ಪ್ರೊಫೈಲ್ ಪುಟಗಳು. ಇಲ್ಲಿ ಯಾವುದನ್ನೂ ತೆರೆದಿಲ್ಲ; ನೀವು ನೋಡುವವರೆಗೆ ಯಾವುದೂ ಪತ್ತೆಯಲ್ಲ."],
  checking: ["Checking…", "ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…"],
};
const KIND = {
  "Court / Legal Archive": ["Court / legal", "ನ್ಯಾಯಾಲಯ"], "Public / Govt Registry": ["Government", "ಸರ್ಕಾರಿ"],
  "News / Media Archive": ["News", "ಸುದ್ದಿ"], "Social / Digital Surface": ["Social media", "ಸಾಮಾಜಿಕ ಜಾಲತಾಣ"],
  "Commercial / Marketplace": ["Marketplace", "ಮಾರುಕಟ್ಟೆ"], "Open Web Surface": ["Website", "ವೆಬ್‌ಸೈಟ್"],
};
const STATUS = { found: [["Found", "ಸಿಕ್ಕಿದೆ"], "ok"], none: [["Not found", "ಸಿಕ್ಕಿಲ್ಲ"], "no"], unreached: [["Not reached", "ತಲುಪಲಿಲ್ಲ"], "na"] };
const WEIGHT = { Strong: "ಬಲವಾದ", Medium: "ಮಧ್ಯಮ", Weak: "ದುರ್ಬಲ" };
const weight = (c) => (c >= 0.75 ? "Strong" : c >= 0.55 ? "Medium" : "Weak");
const when = (iso) => { try { return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); } catch { return ""; } };

export function reportText(r, officer) {
  const b = r.brief || {};
  const w = r.web || {};
  const fd = r.forensic_decoder || {};
  const n = r.statutory_requisition || {};
  return [
    "KSP OSINT LEAD SHEET (unverified open-source leads, not evidence)",
    "================================================================",
    `Prepared: ${new Date().toLocaleString("en-IN")} · Officer: ${officer}`,
    `Searched: ${r.query} · ${fd.target_label || ""} (${fd.normalized || r.query})`,
    "",
    "SUMMARY",
    `What it is: ${b.what || "-"}`,
    `Open web: ${b.web || "-"}`,
    ...(b.live || []).map((l) => `Checked live - ${l.name}: ${l.say}`),
    ...(b.flags?.length ? ["", "POINTS TO NOTE", ...b.flags.map((f) => `- ${f}`)] : []),
    "",
    "NEXT STEPS",
    ...(b.next || []).map((s, i) => `${i + 1}. ${s}`),
    "",
    `OPEN-WEB PAGES THAT MENTION IT (${(w.claims || []).length} of ${w.pages_checked || 0} checked)`,
    ...(w.claims || []).map((c, i) => `[${i + 1}] ${(KIND[c.category] || KIND["Open Web Surface"])[0]} · ${c.domain} · matched ${c.matched_on} · ${weight(c.confidence)}\n    ${c.title}\n    ${c.source_url}`),
    "",
    "LIVE REGISTRY CHECKS",
    ...(r.live_checks || []).map((c) => `- ${c.name} (${c.source}): ${STATUS[c.status]?.[0]?.[0] || c.status}. ${c.say}\n` + (c.facts || []).map((f) => `    ${f.label}: ${f.value}`).join("\n")),
    "",
    "OFFICIAL CHECKS TO RUN",
    ...(r.official_checks || []).map((o) => `- ${o.name}: ${o.what} ${o.how} (${o.url})`),
    ...(n.available ? ["", `NOTICE DRAFT - ${n.statute}`, `To: ${n.recipient}`, n.template_text] : []),
  ].join("\n");
}

export default function OsintReport({ r, web, loading, kn, onCopy, onAudit }) {
  const [tab, setTab] = useState("pages");
  const [copied, setCopied] = useState("");
  if (!r) return null;
  if (r.refused) return <div className="sx-osint-empty"><p>{r.reason}</p></div>;
  const t = (k) => T[k][kn ? 1 : 0];
  const kind = (c) => (KIND[c] || KIND["Open Web Surface"])[kn ? 1 : 0];
  const status = (s) => (STATUS[s]?.[0] || [s, s])[kn ? 1 : 0];
  const b = r.brief;
  const w = r.web || web || {};      // the server's own result carries the page counts and the engine
  const claims = w.claims || [];
  const live = r.live_checks || [];
  const official = r.official_checks || [];
  const notice = r.statutory_requisition || {};
  const fd = r.forensic_decoder || {};

  const copy = async (text, what) => {
    try { await navigator.clipboard.writeText(text); setCopied(what); setTimeout(() => setCopied(""), 1600); } catch { /* no clipboard */ }
    onAudit?.(`Copied ${what} for "${r.query}"`);
  };

  const tabs = [
    ["pages", t("tPages"), claims.length],
    ["live", t("tLive"), live.length],
    ["official", t("tOfficial"), official.length],
    ["details", t("tDetails"), null],
    ["notice", t("tNotice"), notice.available ? 1 : 0],
    ["profiles", t("tProfiles"), (r.sherlock_handles || []).length],
    ["log", t("tLog"), (r.bbot_scan_tree || []).length],
  ].filter(([k, , n]) => k === "pages" || k === "details" || k === "log" || n);

  return (
    <div className="osr">
      {/* The officer's summary */}
      {b && (
        <section className="osr-brief" aria-label="Summary">
          <header>
            <div>
              <span className="osr-type">{fd.target_label}</span>
              <h3>{fd.normalized || r.query}</h3>
            </div>
            <button type="button" className="sx-anchor-btn" onClick={() => onCopy ? onCopy() : copy(reportText(r, ""), "the lead sheet")}>
              {copied === "the lead sheet" ? t("copied") : t("copySheet")}
            </button>
          </header>
          <dl>
            <div><dt>{t("whatItIs")}</dt><dd>{b.what}</dd></div>
            <div><dt>{t("openWeb")}</dt><dd>{b.web}</dd></div>
            {b.live?.map((l) => (
              <div key={l.name}><dt>{l.name}</dt><dd><i className={`osr-st ${STATUS[l.status]?.[1] || "na"}`}>{status(l.status)}</i> {l.say}</dd></div>
            ))}
          </dl>
          {b.flags?.length > 0 && (
            <div className="osr-flags">
              <b>{t("notes")}</b>
              <ul>{b.flags.map((f, i) => <li key={i}>{f}</li>)}</ul>
            </div>
          )}
          {b.next?.length > 0 && (
            <div className="osr-next">
              <b>{t("next")}</b>
              <ol>{b.next.map((s, i) => <li key={i}>{s}</li>)}</ol>
            </div>
          )}
          <p className="osr-foot">{t("foot")}</p>
        </section>
      )}

      <div className="osr-tabs" role="tablist">
        {tabs.map(([k, label, n]) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>
            {label}{n ? <i>{n}</i> : null}
          </button>
        ))}
      </div>

      <div className="osr-body">
        {tab === "pages" && (
          <>
            <p className="osr-note">
              {w.reached === false
                ? t("unreached")
                : `${w.pages_checked || 0} ${t("checked")}${w.engine ? ` (${w.engine})` : ""}; ${claims.length} ${t("contain")}`
                  + (w.dropped_unrelated ? `, ${w.dropped_unrelated} ${t("dropped")}` : "") + "."}
              {w.searched_forms?.length > 0 && <> {t("searchedFor")} {w.searched_forms.map((f) => <code key={f}>{f}</code>)}</>}
            </p>
            {claims.length === 0 && w.reached !== false && (
              <div className="osr-empty">{t("noPage")}</div>
            )}
            {claims.map((c, i) => (
              <article className="osr-page" key={i}>
                <header>
                  <span className="kind">{kind(c.category)}</span>
                  <span className="dom">{c.domain}</span>
                  <span className={`wt w-${weight(c.confidence).toLowerCase()}`} title={t("weightTip")}>
                    {kn ? WEIGHT[weight(c.confidence)] : weight(c.confidence)} · {Math.round(c.confidence * 100)}%
                  </span>
                </header>
                <a className="ttl" href={c.source_url} target="_blank" rel="noopener noreferrer nofollow">{c.title} ↗</a>
                <p>{c.claim}</p>
                <footer>
                  <span>{t("matched")} {c.matched_on}</span>
                  {c.matched_keywords?.length > 0 && <span className="risk">{t("alsoMentions")} {c.matched_keywords.join(", ")}</span>}
                  <span className="hash" title={t("hashTip")}>#{c.evidence_sha256}</span>
                </footer>
              </article>
            ))}
          </>
        )}

        {tab === "live" && (
          <>
            <p className="osr-note">{t("liveNote")}</p>
            {live.map((c) => (
              <article className="osr-live" key={c.name}>
                <header>
                  <b>{c.name}</b>
                  <i className={`osr-st ${STATUS[c.status]?.[1] || "na"}`}>{status(c.status)}</i>
                </header>
                <p>{c.say}</p>
                {c.facts?.length > 0 && (
                  <dl>{c.facts.map((f) => <div key={f.label}><dt>{f.label}</dt><dd>{f.value}</dd></div>)}</dl>
                )}
                <footer>
                  <span>{t("source")} {c.source}</span>
                  {c.source_url && <a href={c.source_url} target="_blank" rel="noopener noreferrer nofollow">{t("open")}</a>}
                  <span>{when(c.checked_at)}</span>
                </footer>
              </article>
            ))}
          </>
        )}

        {tab === "official" && (
          <>
            <p className="osr-note">{t("offNote")}</p>
            {official.map((o) => (
              <article className="osr-off" key={o.name}>
                <header>
                  <b>{o.name}</b>
                  <a className="sx-anchor-btn" href={o.url} target="_blank" rel="noopener noreferrer nofollow"
                     onClick={() => onAudit?.(`Opened ${o.name} for "${r.query}"`)}>{t("openBtn")}</a>
                </header>
                <p><span>{t("tellsYou")}</span>{o.what}</p>
                <p><span>{t("how")}</span>{o.how}</p>
                {o.value && (
                  <button type="button" className="osr-val" onClick={() => copy(String(o.value), o.name)}>
                    {copied === o.name ? t("copied") : <>{t("copyVal")} <code>{o.value}</code> {t("toPaste")}</>}
                  </button>
                )}
              </article>
            ))}
          </>
        )}

        {tab === "details" && (
          <>
            <p className="osr-note">{t("detailsNote")}</p>
            <dl className="osr-grid">
              {(fd.decoded_fields || []).map((f) => <div key={f.label}><dt>{f.label}</dt><dd>{f.value}</dd></div>)}
            </dl>
          </>
        )}

        {tab === "notice" && notice.available && (
          <>
            <div className="osr-notice-hd">
              <div><b>{notice.statute}</b><span>{t("to")} {notice.recipient}</span><span>{t("subject")} {notice.subject}</span></div>
              <button type="button" className="sx-anchor-btn" onClick={() => copy(notice.template_text, "the notice")}>{copied === "the notice" ? t("copied") : t("copyNotice")}</button>
            </div>
            <pre className="osr-pre">{notice.template_text}</pre>
            <p className="osr-note">{t("noticeNote")}</p>
          </>
        )}

        {tab === "profiles" && (
          <>
            <p className="osr-note">{t("profNote")}</p>
            {(r.sherlock_handles || []).map((h) => (
              <div className="osr-prof" key={h.platform}>
                <span><b>{h.platform}</b> <em>{h.category}</em></span>
                {/^https?:\/\//i.test(h.url || "") && <a href={h.url} target="_blank" rel="noopener noreferrer nofollow">{t("open")}</a>}
              </div>
            ))}
          </>
        )}

        {tab === "log" && (
          <ol className="osr-log">
            {(r.bbot_scan_tree || []).map((e, i) => <li key={e.id || i}><span>{when(e.timestamp)}</span>{e.detail}</li>)}
          </ol>
        )}
      </div>
      {loading && <div className="osr-busy">{t("checking")}</div>}
    </div>
  );
}
