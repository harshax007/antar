"use client";
// Money trail (shown as a view of the Search screen, /search?view=money): follow money between accounts - who paid whom, how fast it moved on, where it
// ended up, and the FIRs each account is named in. Data from /api/funds/* (app/services/
// money_trail.py); every flag is a counted rule, shown in words with its numbers.
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useLang } from "@/components/Providers";
import { KIND, rupees } from "@/components/MoneyGraph";
import "@/components/editorial-money.css";

const MoneyGraph = dynamic(() => import("@/components/MoneyGraph"), { ssr: false });
const API = process.env.NEXT_PUBLIC_API_URL || "";

const get = async (path) => {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) {
    const b = await r.json().catch(() => ({}));
    throw Object.assign(new Error(b.detail || "error"), { status: r.status });
  }
  return r.json();
};
const when = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
};
const PURPOSE = {
  payment: ["Paid in", "ಪಾವತಿ"], layering: ["Moved on", "ಮುಂದೆ ಸಾಗಿಸಲಾಗಿದೆ"], collection: ["Collected", "ಸಂಗ್ರಹ"],
  payout: ["Paid out", "ಹೊರಪಾವತಿ"], cash_withdrawal: ["Cash withdrawn", "ನಗದು ಹಿಂಪಡೆತ"],
};

const HOW = {
  named: ["UPI named in the FIR", "FIR ನಲ್ಲಿ UPI ಹೆಸರಿಸಲಾಗಿದೆ"],
  money: ["Money from this complaint", "ಈ ದೂರಿನ ಹಣ"],
  named_and_money: ["Named, and its money", "ಹೆಸರಿಸಲಾಗಿದೆ ಮತ್ತು ಹಣ"],
};

// The FIRs an account or a trail is tied to, newest first, with how each is tied.
// A FIR this copy of the register does not hold (it keeps 2022 on) is shown, not opened.
function FirList({ firs, L, onOpen, limit }) {
  const [all, setAll] = useState(false);
  const shown = all ? firs : firs.slice(0, limit);
  return (
    <>
      <ul className="mt-firs">
        {shown.map((f) => {
          const meta = [f.date, f.district, f.crime, f.stage].filter(Boolean).join(" · ");
          return (
            <li key={f.fir_id}>
              <button type="button" onClick={() => onOpen(f.fir_id)} disabled={!f.date}>
                <b>FIR {f.fir_id}{f.amount ? <em className="mt-fir-amt">{rupees(f.amount)}</em> : null}</b>
                <span>{meta || L("Not in this copy of the register", "ಈ ನೋಂದಣಿ ಪ್ರತಿಯಲ್ಲಿ ಇಲ್ಲ")}</span>
                {f.how && <span className="mt-how">{L(...HOW[f.how])}</span>}
              </button>
            </li>
          );
        })}
      </ul>
      {firs.length > limit && (
        <button type="button" className="mt-more" onClick={() => setAll(!all)}>
          {all ? L("Show fewer", "ಕಡಿಮೆ ತೋರಿಸಿ") : L(`Show all ${firs.length}`, `ಎಲ್ಲಾ ${firs.length} ತೋರಿಸಿ`)}
        </button>
      )}
    </>
  );
}

const holdText = (h, L) => (h < 1 ? L("left within the hour", "ಒಂದು ಗಂಟೆಯೊಳಗೆ ಹೊರಟಿತು")
  : h <= 48 ? L(`left ${Math.round(h)} h after arriving`, `ಬಂದ ${Math.round(h)} ಗಂ. ನಂತರ ಹೊರಟಿತು`)
  : L(`held ${Math.round(h / 24)} days`, `${Math.round(h / 24)} ದಿನ ಇತ್ತು`));

// The account's money in time order, a day per group: what came in, what went on, and how
// long it stayed - the hold time is what tells a mule from a real account.
function Timeline({ rows, L, onPick }) {
  const [all, setAll] = useState(false);
  const days = useMemo(() => {
    const out = [];
    for (const r of rows) {
      const d = String(r.ts).slice(0, 10);
      if (!out.length || out[out.length - 1].day !== d) out.push({ day: d, rows: [], in: 0, out: 0 });
      const g = out[out.length - 1];
      g.rows.push(r);
      g[r.dir] += r.amount;
    }
    return out;
  }, [rows]);
  if (!rows.length) return <p className="mt-sub">{L("No money moved through this account.", "ಈ ಖಾತೆಯ ಮೂಲಕ ಹಣ ಸಾಗಿಲ್ಲ.")}</p>;
  const shown = all ? days : days.slice(-8);
  const day = (d) => new Date(`${d}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  return (
    <>
      {days.length > shown.length && (
        <button type="button" className="mt-more" onClick={() => setAll(true)}>
          {L(`Show ${days.length - shown.length} earlier days`, `ಹಿಂದಿನ ${days.length - shown.length} ದಿನಗಳನ್ನು ತೋರಿಸಿ`)}
        </button>
      )}
      <ol className="mt-tl">
        {shown.map((g) => (
          <li key={g.day}>
            <div className="mt-tl-day">
              <b>{day(g.day)}</b>
              <span>{g.in ? <em className="in">+{rupees(g.in)}</em> : null}{g.out ? <em className="out">−{rupees(g.out)}</em> : null}</span>
            </div>
            <ul>
              {g.rows.map((r, i) => (
                <li key={i} className={r.dir}>
                  <span className="t">{String(r.ts).slice(11, 16)}</span>
                  <span className="amt">{r.dir === "in" ? "+" : "−"}{rupees(r.amount)}</span>
                  <span className="who">{r.dir === "in" ? L("from", "ಇಂದ") : L("to", "ಗೆ")} <button type="button" onClick={() => onPick(r.other)}>{r.other}</button>
                    <small>{r.channel} · {L(...(PURPOSE[r.purpose] || [r.purpose, r.purpose]))}{r.held_h != null ? ` · ${holdText(r.held_h, L)}` : ""}</small>
                  </span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </>
  );
}

export default function MoneyTrail() {
  const router = useRouter();
  const sp = useSearchParams();
  const { lang } = useLang();
  const kn = lang === "kn";
  const L = (en, k) => (kn ? k : en);
  const [ov, setOv] = useState(null);
  const [err, setErr] = useState(null);
  const [root, setRoot] = useState(sp?.get("account") || null);
  const [depth, setDepth] = useState(2);
  const [trail, setTrail] = useState(null);
  const [sel, setSel] = useState(null);
  const [acct, setAcct] = useState(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState(null);

  useEffect(() => {
    get("/api/funds/overview?limit=40").then((o) => {
      setOv(o);
      setRoot((r) => r || o.top?.[0]?.account_id || null);
    }).catch((e) => setErr(e));
  }, []);

  useEffect(() => {
    if (!root) return;
    setTrail(null); setSel(root);
    get(`/api/funds/trail?account=${encodeURIComponent(root)}&depth=${depth}`).then(setTrail).catch((e) => setErr(e));
  }, [root, depth]);

  useEffect(() => {
    if (!sel) return;
    setAcct(null);
    get(`/api/funds/account/${encodeURIComponent(sel)}`).then(setAcct).catch(() => setAcct({ error: true }));
  }, [sel]);

  const doSearch = (e) => {
    e?.preventDefault();
    if (q.trim().length < 2) return;
    get(`/api/funds/search?q=${encodeURIComponent(q.trim())}`).then((r) => setHits(r.results || [])).catch(() => setHits([]));
  };

  const legend = useMemo(() => Object.entries(KIND), []);
  const openFir = (id) => router.push(`/case?id=${encodeURIComponent(id)}`);

  if (err && !ov) {
    return (
      <section className="mt-page"><div className="mt-wrap">
        <h1 className="mt-title">{L(<>Search · <em>Money Trail</em></>, <>ಹುಡುಕಾಟ · <em>ಹಣದ ಜಾಡು</em></>)}</h1>
        <p className="mt-lede">{err.status === 403 ? L("The money trail needs Inspector access or above.", "ಹಣದ ಜಾಡಿಗೆ ಇನ್ಸ್‌ಪೆಕ್ಟರ್ ಅಥವಾ ಮೇಲಿನ ಪ್ರವೇಶ ಬೇಕು.") : err.message}</p>
      </div></section>
    );
  }

  return (
    <section className="mt-page">
      <div className="mt-wrap">
        {/* heading on the left, the four figures on the right: the width is used */}
        <header className="mt-head mt-head--split">
          <div className="mt-head-l">
          <h1 className="mt-title">{L(<>Search · <em>Money Trail</em></>, <>ಹುಡುಕಾಟ · <em>ಹಣದ ಜಾಡು</em></>)}</h1>
          <p className="mt-lede">{L(<>Trace where money went after a UPI fraud:<br />which accounts received it, where they sent it, and the FIRs they appear in.</>,
                                   <>UPI ವಂಚನೆಯ ನಂತರ ಹಣ ಎಲ್ಲಿ ಹೋಯಿತು ಎಂದು ಪತ್ತೆಹಚ್ಚಿ:<br />ಯಾವ ಖಾತೆಗಳು ಪಡೆದವು, ಎಲ್ಲಿಗೆ ಕಳುಹಿಸಿದವು, ಯಾವ FIR ಗಳಲ್ಲಿವೆ.</>)}</p>
          </div>
          {ov && (
            <dl className="mt-stats">
              <div><dt>{L("Money traced", "ಪತ್ತೆಹಚ್ಚಿದ ಹಣ")}</dt><dd>{rupees(ov.amount)}</dd></div>
              <div><dt>{L("Transactions", "ವಹಿವಾಟುಗಳು")}</dt><dd>{ov.transactions.toLocaleString("en-IN")}</dd></div>
              <div><dt>{L("FIRs linked", "ಸಂಬಂಧಿತ FIR")}</dt><dd>{ov.firs.toLocaleString("en-IN")}</dd></div>
              <div><dt>{L("Accounts with warning signs", "ಎಚ್ಚರಿಕೆಯ ಖಾತೆಗಳು")}</dt><dd>{ov.flagged}</dd></div>
            </dl>
          )}
        </header>


        <div className="mt-grid">
          <aside className="mt-list" aria-labelledby="mt-h-list">
            <h2 className="mt-h" id="mt-h-list"><span>01</span>{L("Accounts worth a look", "ಗಮನಿಸಬೇಕಾದ ಖಾತೆಗಳು")}</h2>
            <p className="mt-sub">{L("Most warning signs first, then the most money received.", "ಹೆಚ್ಚು ಎಚ್ಚರಿಕೆಗಳು ಮೊದಲು, ನಂತರ ಹೆಚ್ಚು ಹಣ ಪಡೆದವು.")}</p>
            <form className="mt-search" onSubmit={doSearch} role="search">
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={L("UPI ID, account, FIR or suspect id", "UPI ಐಡಿ, ಖಾತೆ, FIR ಅಥವಾ ಶಂಕಿತ ಐಡಿ")}
                     aria-label={L("Find an account", "ಖಾತೆ ಹುಡುಕಿ")} />
              <button type="submit" className="ui-btn ui-btn--secondary ui-btn--sm">{L("Find", "ಹುಡುಕಿ")}</button>
            </form>
            {hits && (
              <div className="mt-hits">
                {hits.length === 0 ? <p className="mt-none">{L("No account matches.", "ಯಾವುದೇ ಖಾತೆ ಹೊಂದುವುದಿಲ್ಲ.")}</p> : hits.map((h) => (
                  <button key={h.account_id} type="button" onClick={() => { setRoot(h.account_id); setHits(null); }}>
                    <b>{h.account_id}</b><span>{L(KIND[h.kind]?.en || h.kind, KIND[h.kind]?.kn || h.kind)}{h.district ? ` · ${h.district}` : ""}</span>
                  </button>
                ))}
              </div>
            )}
            <ol className="mt-accounts">
              {(ov?.top || []).map((a) => (
                <li key={a.account_id} className={a.account_id === root ? "on" : ""}>
                  <button type="button" onClick={() => setRoot(a.account_id)}>
                    <span className="row"><b>{a.account_id}</b><em>{rupees(a.total_in)}</em></span>
                    <span className="meta">{[a.district, a.firs ? L(`${a.firs} FIRs`, `${a.firs} FIR`) : null, L(`${a.senders} senders`, `${a.senders} ಕಳುಹಿಸಿದವರು`)].filter(Boolean).join(" · ")}</span>
                    {a.flag_titles.length > 0 && (
                      <span className="warn">{L(`${a.flag_titles.length} warning ${a.flag_titles.length === 1 ? "sign" : "signs"}`, `${a.flag_titles.length} ಎಚ್ಚರಿಕೆ`)}
                        <span>{a.flag_titles.join(" · ")}</span></span>
                    )}
                  </button>
                </li>
              ))}
            </ol>
          </aside>

          <section className="mt-graphwrap" aria-labelledby="mt-h-graph">
            <h2 className="mt-h" id="mt-h-graph"><span>02</span>{L("How the money moved", "ಹಣ ಹೇಗೆ ಸಾಗಿತು")}</h2>
            <div className="mt-graphbar">
              <p className="mt-sub">{L("From", "ಇಂದ")} <b>{root || "…"}</b>. {L("Click an account to read it in 03.", "03 ರಲ್ಲಿ ಓದಲು ಖಾತೆ ಕ್ಲಿಕ್ ಮಾಡಿ.")}</p>
              <div className="mt-depth" role="group" aria-label={L("How far to follow", "ಎಷ್ಟು ದೂರ ಅನುಸರಿಸಬೇಕು")}>
                {[1, 2, 3].map((d) => (
                  <button key={d} type="button" className={depth === d ? "on" : ""} aria-pressed={depth === d} onClick={() => setDepth(d)}>
                    {L(`${d} ${d === 1 ? "step" : "steps"}`, `${d} ಹಂತ`)}
                  </button>
                ))}
              </div>
            </div>
            {trail ? <MoneyGraph data={trail} selected={sel} onSelect={setSel} /> : <div className="mt-canvas mt-loading">{L("Following the money…", "ಹಣವನ್ನು ಅನುಸರಿಸಲಾಗುತ್ತಿದೆ…")}</div>}
            <ul className="mt-legend">
              {legend.map(([k, v]) => <li key={k}><i style={{ background: v.border }} />{kn ? v.kn : v.en}</li>)}
              <li className="note">{L("Arrow width: money moved", "ಬಾಣದ ಅಗಲ: ಸಾಗಿದ ಹಣ")}</li>
            </ul>
            {trail?.truncated && <p className="mt-sub">{L("Showing the 70 closest accounts. Pick one to follow it further.", "ಹತ್ತಿರದ 70 ಖಾತೆಗಳನ್ನು ತೋರಿಸಲಾಗಿದೆ.")}</p>}
            {trail?.summary?.length > 0 && (
              <div className="mt-plain">
                <h3>{L("This trail in plain words", "ಈ ಜಾಡು ಸರಳವಾಗಿ")}</h3>
                <ul>{trail.summary.map((s, i) => <li key={i}>{s}</li>)}</ul>
                {trail.sinks?.length > 0 && (
                  <p className="mt-sinks">{L("Where it stops:", "ಹಣ ನಿಲ್ಲುವ ಖಾತೆಗಳು:")}{" "}
                    {trail.sinks.map((s) => <button key={s} type="button" onClick={() => setSel(s)}>{s}</button>)}
                  </p>
                )}
              </div>
            )}
            {trail?.firs?.length > 0 && (
              <details className="mt-trailfirs">
                <summary>{L(`FIRs on this trail (${trail.firs_total})`, `ಈ ಜಾಡಿನ FIR ಗಳು (${trail.firs_total})`)}</summary>
                <FirList firs={trail.firs} L={L} onOpen={openFir} limit={12} />
              </details>
            )}
          </section>

          <aside className="mt-detail" aria-live="polite" aria-labelledby="mt-h-acct">
            <h2 className="mt-h" id="mt-h-acct"><span>03</span>{L("The account", "ಖಾತೆ")}</h2>
            {!acct ? <p className="mt-sub">{L("Reading the account…", "ಖಾತೆ ಓದಲಾಗುತ್ತಿದೆ…")}</p> : acct.error ? <p className="mt-sub">{L("The account could not be read.", "ಖಾತೆಯನ್ನು ಓದಲಾಗಲಿಲ್ಲ.")}</p> : (
              <>
                <span className="mt-kind"><i style={{ background: KIND[acct.account.kind]?.border }} />{L(KIND[acct.account.kind]?.en, KIND[acct.account.kind]?.kn)}</span>
                <p className="mt-acct">{acct.account.account_id}</p>
                <p className="mt-sub">{[acct.account.label !== acct.account.account_id ? acct.account.label : null, acct.account.district,
                  acct.account.bank && !/^(bank|upi)$/i.test(acct.account.bank) ? acct.account.bank : null].filter(Boolean).join(" · ")}</p>
                {acct.suspect && <p className="mt-sus">{L("Held by", "ಹೊಂದಿರುವವರು")} <b>{acct.suspect.full_name || acct.suspect.suspect_id}</b> ({acct.suspect.suspect_id}){acct.suspect.prior_count != null ? L(`, ${acct.suspect.prior_count} prior cases`, `, ${acct.suspect.prior_count} ಹಿಂದಿನ ಪ್ರಕರಣಗಳು`) : ""}</p>}
                <dl className="mt-facts">
                  <div><dt>{L("Money in", "ಬಂದ ಹಣ")}</dt><dd>{rupees(acct.total_in)}<small>{L(`${acct.count_in} from ${acct.senders} accounts`, `${acct.senders} ಖಾತೆಗಳಿಂದ ${acct.count_in}`)}</small></dd></div>
                  <div><dt>{L("Money out", "ಹೋದ ಹಣ")}</dt><dd>{rupees(acct.total_out)}<small>{L(`${acct.count_out} to ${acct.receivers} accounts`, `${acct.receivers} ಖಾತೆಗಳಿಗೆ ${acct.count_out}`)}</small></dd></div>
                  {acct.first && <div><dt>{L("Active", "ಸಕ್ರಿಯ")}</dt><dd className="sm">{when(acct.first).split(",")[0]} – {when(acct.last).split(",")[0]}</dd></div>}
                </dl>
                {acct.summary && (
                  <div className="mt-plain">
                    <h3>{L("What this account did", "ಈ ಖಾತೆ ಏನು ಮಾಡಿತು")}</h3>
                    <ul>{acct.summary.lines.map((s, i) => <li key={i}>{s}</li>)}</ul>
                    {acct.summary.next_steps.length > 0 && (
                      <>
                        <h4>{L("What to ask for next", "ಮುಂದೆ ಏನು ಕೇಳಬೇಕು")}</h4>
                        <ol className="mt-steps">{acct.summary.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
                      </>
                    )}
                    <p className="mt-note">{L(acct.summary.note, "ಎಣಿಸಿದ ವಹಿವಾಟುಗಳಿಂದ ಸುಳಿವುಗಳು, ತೀರ್ಮಾನಗಳಲ್ಲ. ಕ್ರಮಕ್ಕೆ ಮೊದಲು ಬ್ಯಾಂಕ್ ದಾಖಲೆಗಳೊಂದಿಗೆ ದೃಢೀಕರಿಸಿ.")}</p>
                  </div>
                )}
                {acct.flags.length > 0 && (
                  <>
                    <h3>{L("Warning signs", "ಎಚ್ಚರಿಕೆ ಸೂಚನೆಗಳು")}</h3>
                    <ol className="mt-flags">{acct.flags.map((f, k) => <li key={f.key}><span className="n">{String(k + 1).padStart(2, "0")}</span><b>{f.title}</b><span className="d">{f.detail}</span></li>)}</ol>
                  </>
                )}
                {(acct.linked_firs || acct.firs).length > 0 && (
                  <>
                    <h3>{L(`Linked FIRs (${acct.linked_firs_total ?? acct.firs.length})`, `ಸಂಬಂಧಿತ FIR ಗಳು (${acct.linked_firs_total ?? acct.firs.length})`)}</h3>
                    <FirList firs={acct.linked_firs || acct.firs} L={L} onOpen={openFir} limit={8} />
                  </>
                )}
                <h3>{L("Timeline of the money", "ಹಣದ ಕಾಲರೇಖೆ")}</h3>
                <Timeline rows={acct.timeline || []} L={L} onPick={setSel} />
                {!acct.timeline && (
                <ul className="mt-tx">
                  {acct.transactions.slice(0, 25).map((t) => {
                    const inbound = t.to_account === acct.account.account_id;
                    const other = inbound ? t.from_account : t.to_account;
                    return (
                      <li key={t.txn_id} className={inbound ? "in" : "out"}>
                        <span className="amt">{inbound ? "+" : "−"}{rupees(t.amount_inr)}</span>
                        <span className="who">{inbound ? L("from", "ಇಂದ") : L("to", "ಗೆ")} <button type="button" onClick={() => setSel(other)}>{other}</button></span>
                        <span className="when">{when(t.ts)} · {t.channel} · {L(...(PURPOSE[t.purpose] || [t.purpose, t.purpose]))}</span>
                      </li>
                    );
                  })}
                </ul>
                )}
                {acct.account.account_id !== root && (
                  <div className="mt-actions">
                    <button type="button" className="ui-btn ui-btn--secondary ui-btn--sm" onClick={() => setRoot(acct.account.account_id)}>
                      {L("Follow the money from here", "ಇಲ್ಲಿಂದ ಹಣವನ್ನು ಅನುಸರಿಸಿ")}
                    </button>
                  </div>
                )}
              </>
            )}
          </aside>
        </div>
      </div>
    </section>
  );
}
