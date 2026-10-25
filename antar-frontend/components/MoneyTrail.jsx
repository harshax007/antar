"use client";
// Money trail (shown as a view of the Search screen, /search?view=money): follow money between accounts - who paid whom, how fast it moved on, where it
// ended up, and the FIRs each account is named in. Data from /api/money/* (app/services/
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
    get("/api/money/overview?limit=40").then((o) => {
      setOv(o);
      setRoot((r) => r || o.top?.[0]?.account_id || null);
    }).catch((e) => setErr(e));
  }, []);

  useEffect(() => {
    if (!root) return;
    setTrail(null); setSel(root);
    get(`/api/money/trail?account=${encodeURIComponent(root)}&depth=${depth}`).then(setTrail).catch((e) => setErr(e));
  }, [root, depth]);

  useEffect(() => {
    if (!sel) return;
    setAcct(null);
    get(`/api/money/account/${encodeURIComponent(sel)}`).then(setAcct).catch(() => setAcct({ error: true }));
  }, [sel]);

  const doSearch = (e) => {
    e?.preventDefault();
    if (q.trim().length < 2) return;
    get(`/api/money/search?q=${encodeURIComponent(q.trim())}`).then((r) => setHits(r.results || [])).catch(() => setHits([]));
  };

  const legend = useMemo(() => Object.entries(KIND), []);

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
          <p className="mt-lede">{L("Trace where money went after a UPI fraud: which accounts received it, where they sent it, and the FIRs they appear in.",
                                   "UPI ವಂಚನೆಯ ನಂತರ ಹಣ ಎಲ್ಲಿ ಹೋಯಿತು ಎಂದು ಪತ್ತೆಹಚ್ಚಿ: ಯಾವ ಖಾತೆಗಳು ಪಡೆದವು, ಎಲ್ಲಿಗೆ ಕಳುಹಿಸಿದವು, ಯಾವ FIR ಗಳಲ್ಲಿವೆ.")}</p>
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
                {acct.flags.length > 0 && (
                  <>
                    <h3>{L("Warning signs", "ಎಚ್ಚರಿಕೆ ಸೂಚನೆಗಳು")}</h3>
                    <ol className="mt-flags">{acct.flags.map((f, k) => <li key={f.key}><span className="n">{String(k + 1).padStart(2, "0")}</span><b>{f.title}</b><span className="d">{f.detail}</span></li>)}</ol>
                  </>
                )}
                {acct.firs.length > 0 && (
                  <>
                    <h3>{L("FIRs this account is in", "ಈ ಖಾತೆ ಇರುವ FIR ಗಳು")}</h3>
                    <ul className="mt-firs">
                      {acct.firs.slice(0, 12).map((f) => (
                        <li key={f.fir_id}><button type="button" onClick={() => router.push(`/case/${encodeURIComponent(f.fir_id)}`)}>
                          <b>FIR {f.fir_id}</b><span>{[f.date, f.district, f.crime, f.stage].filter(Boolean).join(" · ")}</span>
                        </button></li>
                      ))}
                    </ul>
                  </>
                )}
                <h3>{L("Transactions", "ವಹಿವಾಟುಗಳು")}</h3>
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
