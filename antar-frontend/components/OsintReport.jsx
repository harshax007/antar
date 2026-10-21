"use client";

import { useState } from "react";

// What one OSINT run found, laid out the way an officer reads it: the summary first (what this
// is, what the open web shows, what was checked live, what to do next), then the detail behind
// each line. Everything here is an unverified lead; nothing is written to the FIR record.

const KIND = {
  "Court / Legal Archive": "Court / legal", "Public / Govt Registry": "Government",
  "News / Media Archive": "News", "Social / Digital Surface": "Social media",
  "Commercial / Marketplace": "Marketplace", "Open Web Surface": "Website",
};
const STATUS = { found: ["Found", "ok"], none: ["Not found", "no"], unreached: ["Not reached", "na"] };
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
    ...(w.claims || []).map((c, i) => `[${i + 1}] ${KIND[c.category] || "Website"} · ${c.domain} · matched ${c.matched_on} · ${weight(c.confidence)}\n    ${c.title}\n    ${c.source_url}`),
    "",
    "LIVE REGISTRY CHECKS",
    ...(r.live_checks || []).map((c) => `- ${c.name} (${c.source}): ${STATUS[c.status]?.[0] || c.status}. ${c.say}\n` + (c.facts || []).map((f) => `    ${f.label}: ${f.value}`).join("\n")),
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
    ["pages", `Open-web pages`, claims.length],
    ["live", "Checked live", live.length],
    ["official", "Official checks", official.length],
    ["details", "What it decodes to", null],
    ["notice", "Notice to send", notice.available ? 1 : 0],
    ["profiles", "Profile links", (r.sherlock_handles || []).length],
    ["log", "Step log", (r.bbot_scan_tree || []).length],
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
              {copied === "the lead sheet" ? "Copied" : "Copy lead sheet"}
            </button>
          </header>
          <dl>
            <div><dt>What it is</dt><dd>{b.what}</dd></div>
            <div><dt>Open web</dt><dd>{b.web}</dd></div>
            {b.live?.map((l) => (
              <div key={l.name}><dt>{l.name}</dt><dd><i className={`osr-st ${STATUS[l.status]?.[1] || "na"}`}>{STATUS[l.status]?.[0] || l.status}</i> {l.say}</dd></div>
            ))}
          </dl>
          {b.flags?.length > 0 && (
            <div className="osr-flags">
              <b>Points to note</b>
              <ul>{b.flags.map((f, i) => <li key={i}>{f}</li>)}</ul>
            </div>
          )}
          {b.next?.length > 0 && (
            <div className="osr-next">
              <b>What to do next</b>
              <ol>{b.next.map((s, i) => <li key={i}>{s}</li>)}</ol>
            </div>
          )}
          <p className="osr-foot">Unverified open-source leads, not evidence. Nothing here is added to the FIR record.</p>
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
                ? "The open-web search could not be reached just now. Run it again in a minute."
                : `${w.pages_checked || 0} pages checked${w.engine ? ` (${w.engine})` : ""}; ${claims.length} contain it`
                  + (w.dropped_unrelated ? `, ${w.dropped_unrelated} did not and were left out` : "") + "."}
              {w.searched_forms?.length > 0 && <> Searched for: {w.searched_forms.map((f) => <code key={f}>{f}</code>)}</>}
            </p>
            {claims.length === 0 && w.reached !== false && (
              <div className="osr-empty">No public page mentions it. That is a result: nothing about this is on the open web that a search can find.</div>
            )}
            {claims.map((c, i) => (
              <article className="osr-page" key={i}>
                <header>
                  <span className="kind">{KIND[c.category] || "Website"}</span>
                  <span className="dom">{c.domain}</span>
                  <span className={`wt w-${weight(c.confidence).toLowerCase()}`} title="How much weight this page deserves: an exact match counts more, and a court, government or news page more than an unknown site">
                    {weight(c.confidence)} · {Math.round(c.confidence * 100)}%
                  </span>
                </header>
                <a className="ttl" href={c.source_url} target="_blank" rel="noopener noreferrer nofollow">{c.title} ↗</a>
                <p>{c.claim}</p>
                <footer>
                  <span>Matched: {c.matched_on}</span>
                  {c.matched_keywords?.length > 0 && <span className="risk">Also mentions: {c.matched_keywords.join(", ")}</span>}
                  <span className="hash" title="Fingerprint of the page address and text as seen, for the record">#{c.evidence_sha256}</span>
                </footer>
              </article>
            ))}
          </>
        )}

        {tab === "live" && (
          <>
            <p className="osr-note">Answered just now by the public registry named on each card. Only the identifier was sent; nothing about the case.</p>
            {live.map((c) => (
              <article className="osr-live" key={c.name}>
                <header>
                  <b>{c.name}</b>
                  <i className={`osr-st ${STATUS[c.status]?.[1] || "na"}`}>{STATUS[c.status]?.[0] || c.status}</i>
                </header>
                <p>{c.say}</p>
                {c.facts?.length > 0 && (
                  <dl>{c.facts.map((f) => <div key={f.label}><dt>{f.label}</dt><dd>{f.value}</dd></div>)}</dl>
                )}
                <footer>
                  <span>Source: {c.source}</span>
                  {c.source_url && <a href={c.source_url} target="_blank" rel="noopener noreferrer nofollow">open ↗</a>}
                  <span>{when(c.checked_at)}</span>
                </footer>
              </article>
            ))}
          </>
        )}

        {tab === "official" && (
          <>
            <p className="osr-note">Government and public portals to check this on. Open each in your own login; Antar does not sign in to them.</p>
            {official.map((o) => (
              <article className="osr-off" key={o.name}>
                <header>
                  <b>{o.name}</b>
                  <a className="sx-anchor-btn" href={o.url} target="_blank" rel="noopener noreferrer nofollow"
                     onClick={() => onAudit?.(`Opened ${o.name} for "${r.query}"`)}>Open ↗</a>
                </header>
                <p><span>Tells you</span>{o.what}</p>
                <p><span>How</span>{o.how}</p>
                {o.value && (
                  <button type="button" className="osr-val" onClick={() => copy(String(o.value), o.name)}>
                    {copied === o.name ? "Copied" : <>Copy <code>{o.value}</code> to paste</>}
                  </button>
                )}
              </article>
            ))}
          </>
        )}

        {tab === "details" && (
          <>
            <p className="osr-note">Worked out from the identifier itself; nothing was looked up for this.</p>
            <dl className="osr-grid">
              {(fd.decoded_fields || []).map((f) => <div key={f.label}><dt>{f.label}</dt><dd>{f.value}</dd></div>)}
            </dl>
          </>
        )}

        {tab === "notice" && notice.available && (
          <>
            <div className="osr-notice-hd">
              <div><b>{notice.statute}</b><span>To: {notice.recipient}</span><span>Subject: {notice.subject}</span></div>
              <button type="button" className="sx-anchor-btn" onClick={() => copy(notice.template_text, "the notice")}>{copied === "the notice" ? "Copied" : "Copy notice"}</button>
            </div>
            <pre className="osr-pre">{notice.template_text}</pre>
            <p className="osr-note">A draft. Check the facts, add the case reference, and send it under the signature of the officer authorised to issue it.</p>
          </>
        )}

        {tab === "profiles" && (
          <>
            <p className="osr-note">Public profile pages to open by hand. None was opened here, so none is a finding until you have looked.</p>
            {(r.sherlock_handles || []).map((h) => (
              <div className="osr-prof" key={h.platform}>
                <span><b>{h.platform}</b> <em>{h.category}</em></span>
                {/^https?:\/\//i.test(h.url || "") && <a href={h.url} target="_blank" rel="noopener noreferrer nofollow">open ↗</a>}
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
      {loading && <div className="osr-busy">Checking…</div>}
    </div>
  );
}
