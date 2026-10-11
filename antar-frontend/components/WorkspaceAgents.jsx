"use client";

// Agents in the Expert workspace.
//
// Two things, kept apart because they are different claims:
//   Worked on this answer   the agents the pipeline reports for THIS answer - nothing is
//                           added to make the list look fuller
//   Take it further         the console agents (the same nine as on the Brain screen), run
//                           here on a record named in the answer or typed by the officer.
//                           An agent that has nothing it can work on says what it needs
//                           instead of running on a guess.
//
// A run goes to POST /api/console/run and comes back in Antar's template: bottom line,
// evidence class, context, evidence, limits. Styles are in app/globals.css (.wa-).

import { useEffect, useMemo, useState } from "react";
import { fetchAPI } from "@/lib/api";

// The character each agent has everywhere else (AgentStrip, the Brain screen).
export const FACE = {
  query: "tv", vault: "tv", network: "gearbot", link: "gearbot", profile: "scout", motive: "scout",
  forecast: "clockwork", predict: "clockwork", prediction: "clockwork", core: "clockwork",
  social: "toaster", sense: "toaster", geo: "drone", pattern: "radio",
  alert_suggest: "lantern", alerts: "lantern", osint: "rocket", research: "postbot", trace: "postbot",
  brain: "crt", recall: "crt", advocate: "knight", advocate_agent: "knight", vigil: "owl",
  corridor: "astronaut", linkage: "cube",
};
const CLASS_NAME = { K: "Known", D: "Derived", I: "Inferred", U: "Unknown" };
const KIND_LABEL = { accused: "accused", station: "station", district: "district", crime_group: "crime type" };
// What each console agent can be pointed at, from its card's `needs`.
const ACCEPTS = { suspect: ["accused"], FIR: ["accused"], station: ["station"], district: ["district"], "crime type": ["crime_group"] };

const SUSPECT_RE = /\b(ACC-[A-Z]{2}-\d{3,}|S\d{4,})\b/g;
const STATION_RE = /\b([A-Z][A-Za-z.]+(?: [A-Z][A-Za-z.]+){0,3} PS)\b/g;
const DISTRICT_RE = /\b([A-Z][a-z]+(?: [A-Z][a-z]+){0,2} (?:City|Dist|District|Railways))\b/g;

// The agents the pipeline names for one answer. When the final event carries no list, the
// steps it reported while answering do: each names the agent that took it. Nothing is added.
export function agentsUsed(usedAgents, trace) {
  const named = (usedAgents || []).length ? usedAgents : (trace || []).map((s) => s?.agent).filter((a) => a && FACE[String(a).toLowerCase()]);
  return [...new Set(named.map((a) => String(a).toLowerCase()))];
}

function Face({ id, size = 26 }) {
  const face = FACE[String(id || "").toLowerCase()];
  if (!face) return null;
  // The middle cell of the 3x3 sheet: the character looking straight ahead.
  return <i className="wa-face" aria-hidden="true"
            style={{ width: size, height: size, backgroundImage: `url(/mascots/sm/${face}-directions.webp)` }} />;
}

// How a typed target is read. Shape only, the same rule the backend applies - nothing is
// looked up by similarity.
function readTyped(text) {
  const t = text.trim();
  if (!t) return null;
  if (/^(ACC-[A-Z0-9-]+|S\d{3,})$/i.test(t)) return { kind: "accused", value: t.toUpperCase() };
  if (/ PS$/i.test(t)) return { kind: "station", value: t };
  if (/ (City|Dist|District|Railways)$/i.test(t)) return { kind: "district", value: t };
  return { kind: "crime_group", value: t.toUpperCase() };
}

export default function WorkspaceAgents({ answer = "", question = "", suspects = [], usedAgents = [], trace = [], kn }) {
  const [cards, setCards] = useState(null);          // console agent cards, or { error }
  const [target, setTarget] = useState(null);        // { kind, value }
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState([]);
  const [results, setResults] = useState([]);        // newest first

  useEffect(() => {
    fetchAPI("/api/console/identity").then((p) => setCards(p.agents || [])).catch((e) => setCards({ error: e.message }));
  }, []);

  // Records this answer names. An id on the answer's suspect list comes first; places and
  // ids are then read out of the question and the answer text.
  const found = useMemo(() => {
    const text = `${question}\n${answer}`.replace(/\*\*/g, "");
    const out = [], seen = new Set();
    const add = (kind, value) => { const k = `${kind}:${value.toLowerCase()}`; if (value && !seen.has(k)) { seen.add(k); out.push({ kind, value }); } };
    suspects.forEach((s) => add("accused", String(s.id || "").toUpperCase()));
    (text.match(SUSPECT_RE) || []).forEach((v) => add("accused", v.toUpperCase()));
    (text.match(STATION_RE) || []).forEach((v) => add("station", v));
    (text.match(DISTRICT_RE) || []).forEach((v) => add("district", v));
    return out.slice(0, 8);
  }, [answer, question, suspects]);

  // A new answer starts clean: the old target and its results belonged to the last one.
  useEffect(() => { setTarget(found[0] || null); setResults([]); }, [answer]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run(agent) {
    if (!target || busy.includes(agent.id)) return;
    setBusy((b) => [...b, agent.id]);
    let r;
    try {
      r = await fetchAPI("/api/console/run", { method: "POST", body: JSON.stringify({ agent: agent.id, target: { [target.kind]: target.value } }) });
    } catch (e) {
      r = { agent: agent.id, name: agent.name, status: "error", bottom_line: `The ${agent.name} agent could not be reached (${e.message}).`, evidence: [], limits: [] };
    }
    setBusy((b) => b.filter((x) => x !== agent.id));
    setResults((rs) => [{ ...r, on: target.value, key: `${agent.id}-${Date.now()}` }, ...rs].slice(0, 8));
  }

  const used = agentsUsed(usedAgents, trace);
  const list = Array.isArray(cards) ? cards : [];

  return (
    <div className="c2-block wa">
      <div className="c2-block-t">{kn ? "ಏಜೆಂಟ್‌ಗಳು" : "Agents"}</div>

      <div className="wa-row">
        <span className="wa-k">{kn ? "ಈ ಉತ್ತರದಲ್ಲಿ ಕೆಲಸ ಮಾಡಿದವು" : "Worked on this answer"}</span>
        <div className="wa-used">
          {used.length ? used.map((a) => (
            <span key={a} className="wa-chip"><Face id={a} size={22} />{a.replace(/_/g, " ")}</span>
          )) : <span className="wa-none">{kn ? "ವರದಿಯಾಗಿಲ್ಲ" : "None reported for this answer."}</span>}
        </div>
      </div>

      <div className="wa-row">
        <span className="wa-k">{kn ? "ಮುಂದುವರಿಸಿ" : "Take it further on"}</span>
        <div className="wa-targets">
          {found.map((t) => (
            <button key={`${t.kind}:${t.value}`} className={`wa-tgt${target && target.kind === t.kind && target.value === t.value ? " on" : ""}`}
                    onClick={() => setTarget(t)} title={KIND_LABEL[t.kind]}>
              <em>{KIND_LABEL[t.kind]}</em>{t.value}
            </button>
          ))}
          <form onSubmit={(e) => { e.preventDefault(); const t = readTyped(typed); if (t) { setTarget(t); setTyped(""); } }}>
            <input value={typed} onChange={(e) => setTyped(e.target.value)} spellCheck={false} autoComplete="off"
                   aria-label="Target for the agents"
                   placeholder={found.length ? (kn ? "ಅಥವಾ ಟೈಪ್ ಮಾಡಿ" : "or type one") : (kn ? "ಆರೋಪಿ ID, ಠಾಣೆ ಅಥವಾ ಜಿಲ್ಲೆ" : "Accused id, station (… PS) or district")} />
          </form>
        </div>
      </div>
      {!found.length && !target && (
        <p className="wa-note">{kn ? "ಈ ಉತ್ತರವು ಯಾವುದೇ ಆರೋಪಿ, ಠಾಣೆ ಅಥವಾ ಜಿಲ್ಲೆಯನ್ನು ಹೆಸರಿಸಿಲ್ಲ. ಏಜೆಂಟ್ ನಡೆಸಲು ಒಂದನ್ನು ಟೈಪ್ ಮಾಡಿ."
          : "This answer names no accused, station or district. Type one to run an agent on it."}</p>
      )}

      {cards?.error && <p className="wa-note">The agents could not be loaded ({cards.error}).</p>}
      <div className="wa-agents">
        {list.map((a) => {
          const ok = !!target && (ACCEPTS[a.needs] || []).includes(target.kind);
          const working = busy.includes(a.id);
          return (
            <button key={a.id} className={`wa-agent${working ? " busy" : ""}`} disabled={!ok || working} onClick={() => run(a)}
                    title={ok ? `${a.purpose} Run on ${target.value}.` : `${a.purpose} Needs a ${a.needs}.`}>
              <Face id={a.id} size={30} />
              <span><b>{a.name}</b><small>{working ? (kn ? "ಕೆಲಸ ಮಾಡುತ್ತಿದೆ…" : "working…") : ok ? `${kn ? "ನಡೆಸಿ" : "run on"} ${target.value}` : `${kn ? "ಬೇಕು" : "needs a"} ${a.needs}`}</small></span>
            </button>
          );
        })}
      </div>

      {results.map((r) => (
        <article key={r.key} className={`wa-res ${r.status || ""}`}>
          <header>
            <Face id={r.agent} size={22} />
            <b>{r.name || r.agent}</b>
            <span>{r.on}</span>
            {r.evidence_class && <i className={`wa-cls ${r.evidence_class}`}>{r.evidence_class} · {CLASS_NAME[r.evidence_class]}</i>}
            {r.status === "refused" && <i className="wa-cls R">not run</i>}
            {r.ms != null && r.status !== "refused" && <em>{r.cached ? "cached" : `${r.ms} ms`}</em>}
          </header>
          <p className="wa-bl">{r.bottom_line}</p>
          {r.context && <p className="wa-cx">{r.context}</p>}
          {r.evidence?.length > 0 && <ul>{r.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>}
          {(r.limits || []).map((x, i) => <p key={i} className="wa-lim">Note: {x}</p>)}
        </article>
      ))}
    </div>
  );
}
