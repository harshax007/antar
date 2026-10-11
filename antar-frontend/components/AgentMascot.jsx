"use client";

// Brain console - the agents on the Brain screen and the Brain terminal.
//
// Nine agents glide over the graph. Each can be picked up and dropped on a record, which
// runs that agent on that record (POST /api/console/run); a click opens its card. The
// terminal takes a fixed command set - the one the backend publishes at
// /api/console/identity - and nothing typed is sent to a model.
//
// Three things here are real rather than decoration:
//   Talking    when an agent finishes it hands the record to the agent it recommends
//              next, and THAT AGENT RUNS. The line on screen is the message that was sent
//              and the reply that came back. One hop per request, so a single drop can
//              never fan out into a chain nobody asked for.
//   Memory     every run is remembered for the browser session: what was asked, of which
//              record, and the bottom line. A repeat run says whether the answer changed.
//   Notifying  a result that lands while the terminal is closed, and any answer that
//              differs from what was remembered, is raised to the officer.
//   Learning   between jobs the agents pass each other what the records show today
//              (GET /api/console/learnings): FIRs dated today, the district and crime group
//              that lead, open alerts, what officers rated. Each line is a count; clicking
//              it opens the terminal with the rows behind it.

import { useCallback, useEffect, useRef, useState } from "react";
import { Mascot } from "page-mascot";
import { fetchAPI } from "@/lib/api";

// Presentation only: what an agent IS comes from the backend identity pack. One colour for
// all of them - an agent is told apart by its face, glyph and name, and state is shown by motion.
const ACCENT = "#22E6F0";
// Each agent's character: two page-mascot sprite sheets in public/mascots (nine head
// directions, nine expressions). The face watches the cursor and reacts when clicked.
const FACE = {
  network: "gearbot", profile: "scout", research: "postbot", advocate: "knight", recall: "crt",
  linkage: "cube", forecast: "clockwork", geo: "drone", pattern: "radio",
};
const FACE_PX = 60;
const ICON = {
  network: "M13 9a4 4 0 112 7l-4 4a4 4 0 11-6-6l2-2m13 0l2-2a4 4 0 00-6-6l-4 4a4 4 0 002 7",
  profile: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM4 21a8 8 0 0116 0",
  research: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  advocate: "M12 3v18M5 7h14M5 7l-3 7a4 4 0 006 0L5 7zm14 0l-3 7a4 4 0 006 0l-3-7z",
  recall: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
  linkage: "M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z",
  forecast: "M3 4h18M4 4v12a1 1 0 001 1h14a1 1 0 001-1V4M7 12l3-3 3 3 4-4M8 21l4-4 4 4",
  geo: "M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0zM15 11a3 3 0 11-6 0 3 3 0 016 0z",
  pattern: "M4 4h6v6H4V4zm10 0h6v6h-6V4zM4 14h6v6H4v-6zm10 0h6v6h-6v-6z",
};
const ORDER = ["network", "profile", "research", "advocate", "recall", "linkage", "forecast", "geo", "pattern"];
const WORDS = ["help", "agents", "about", "select", "run", "fastrun", "assemble", "roam", "memory", "forget", "log", "auto", "notify", "why", "identity", "evolution", "learnings", "history", "think", "connect", "anticipate", "clear"];
// Worked examples per command, for `help <command>` and for the hint under the prompt.
const USAGE = {
  run: ["run network S0041", "run profile ACC-KA-500777", "run geo Bengaluru City", "run forecast Bellanduru PS", "run linkage upi:name@bank", "run network   (uses the selected record)"],
  about: ["about advocate", "about forecast"],
  select: ["select S0041", "select ACC-KA-500777"],
  memory: ["memory", "memory network"],
  auto: ["auto off", "auto on"],
  notify: ["notify on", "notify off"],
  help: ["help", "help run"],
  history: ["history"],
  think: ["think", "/think"],
  connect: ["connect S0041", "connect ACC-KA-500777", "/connect   (uses the selected record)"],
  anticipate: ["anticipate Bellanduru PS", "anticipate Bengaluru City", "/anticipate   (uses the selected record)"],
};
// Which agents a record of each kind can be handed to, in the order worth trying.
const FOR_KIND = { accused: ["network", "profile", "research", "linkage"], station: ["forecast"], district: ["geo"], crime_group: ["pattern"] };
const CLASS_NAME = { K: "Known", D: "Derived", I: "Inferred", U: "Unknown" };

// Slow enough to follow with the eye and read a name tag on the move.
const SPEED = 30, ACCEL = 40, APART = 76;       // px/s, px/s², px between two agents
const FLY_MAX = 620, FLY_PULL = 5;              // Fast Run: top speed in px/s, and how hard an agent is drawn to its place
const MEM_KEY = "antar_console_memory", MEM_MAX = 60;

const nodeLabel = (n) => (n.accused ? n.accused : `${n.crimeHead || n.crimeGroup || "FIR"} · ${n.zone || n.district || ""}`);
// What a record carries. No id is sent: a node's number is only its place in the list the
// graph was drawn from, and means nothing to the backend.
const nodeTarget = (n) => ({
  accused: n.accused || "", vehicle: n.vehicle || "", upi: n.upi || "", ip: n.ip || "",
  station: n.zone || "", district: n.district || "", crime_group: n.crimeGroup || "",
});
const clock = (ts) => new Date(ts).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
const short = (text, n = 96) => (String(text || "").length <= n ? String(text || "") : null);
const memKey = (payload) => (typeof payload === "string" ? payload.trim().toLowerCase() : JSON.stringify(payload));

function loadMemory() {
  try { return JSON.parse(sessionStorage.getItem(MEM_KEY) || "[]"); } catch { return []; }
}

function nearest(word, pool) {
  const w = word.toLowerCase();
  return pool.find((p) => p.startsWith(w) || w.startsWith(p)) || pool.find((p) => p[0] === w[0]) || null;
}

// `agentsOn`  the agents are drawn - on the Brain graph (All Data, and Focus once a record
//             is selected, since a selected record is what a clicked agent works on)
// `consoleOn` the terminal and notices are available - on the Brain graph, not the Crime Graph
// `suggestions` things in the current view worth a look: [{ agent, text, ask, cmd }]
// `flying`    a Fast Run is in progress: the agents leave their places and circle the brain
// `flyAgent`  the agent whose pass the Fast Run is on, shown working while it is
export default function AgentMascot({ controlRef, apiRef, focus, onThink, kn, agentsOn = true, consoleOn = true, suggestions = [], flying = false, flyAgent = null }) {
  const tips = useRef({ list: [], at: 0 });
  useEffect(() => { tips.current = { list: suggestions, at: 0 }; }, [suggestions]);
  // What the records show today. Read on arrival and again every five minutes, so a line
  // said in the afternoon is the afternoon's count.
  const learned = useRef({ date: "", list: [] });
  useEffect(() => {
    let alive = true;
    const pull = () => fetchAPI("/api/console/learnings")
      .then((r) => { if (alive) learned.current = { date: r.date || "", list: r.learnings || [] }; })
      .catch(() => {});                              // older backend, or offline: the agents simply have less to say
    pull();
    const t = setInterval(pull, 300000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const [pack, setPack] = useState(null);          // identity pack, or { error }
  const [open, setOpen] = useState(false);
  const [small, setSmall] = useState(false);
  const [lines, setLines] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState([]);            // agent ids running now
  const [dragging, setDragging] = useState(null);  // agent id while it is being carried
  const [target, setTarget] = useState(null);      // { label, payload }
  const [roam, setRoam] = useState(true);          // agents move over the brain | hold a line
  const [talk, setTalk] = useState(null);          // { from, to, text, key } - the line on screen
  const [toasts, setToasts] = useState([]);        // notifications to the officer
  const [unread, setUnread] = useState(0);
  const lastRun = useRef(null);
  const history = useRef({ items: [], at: 0 });
  const memory = useRef([]);                       // [{ agent, key, label, payload, status, cls, bottom, ts }]
  const comms = useRef([]);                        // [{ ts, from, to, text }] - messages agents really sent
  const prefs = useRef({ auto: true, system: false, roam: true, seen: true });
  const winRef = useRef(null), outRef = useRef(null), inRef = useRef(null);
  const layerRef = useRef(null), hintRef = useRef(null), sayRef = useRef(null), wireRef = useRef(null), packetRef = useRef(null);
  const packet2Ref = useRef(null), packet3Ref = useRef(null);
  const orbitRef = useRef(null);
  const bugEls = useRef({});
  const sim = useRef({ a: {}, queue: [], talk: null, nextIdle: Date.now() + 9000, held: null, moved: false });

  // The Brain page scrolls on to the Data Overview. Nothing of the console follows the
  // officer down there: once the graph is mostly off screen, agents, terminal and notices go.
  const [inView, setInView] = useState(true);
  useEffect(() => {
    const stage = layerRef.current?.parentElement;
    if (!stage || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => setInView(e.intersectionRatio > 0.4), { threshold: [0, 0.4, 1] });
    io.observe(stage);
    return () => io.disconnect();
  }, []);
  const showAgents = agentsOn && inView, showConsole = consoleOn && inView;
  useEffect(() => { prefs.current.drawn = showAgents; }, [showAgents]);

  useEffect(() => { prefs.current.roam = roam; }, [roam]);
  // Fast Run: start the flight when it begins, and let it wind down when it ends. The
  // frame loop below does the flying; this only marks the two moments.
  useEffect(() => {
    const S = sim.current;
    if (flying) {
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) S.fly = { t0: performance.now(), theta: 0, stopAt: 0, p: null };
    } else if (S.fly && !S.fly.stopAt) S.fly.stopAt = performance.now();
  }, [flying]);
  useEffect(() => {
    prefs.current.seen = open && !small;           // is the officer looking at the terminal?
    if (prefs.current.seen) setUnread(0);
  }, [open, small]);
  useEffect(() => { memory.current = loadMemory(); }, []);
  useEffect(() => {
    fetchAPI("/api/console/identity").then(setPack).catch((e) => setPack({ error: e.message || "unreachable" }));
  }, []);
  // A record the officer clicks in the graph becomes the terminal's selected target.
  // Leaving the selection clears it, so a later click on an agent cannot run on a record
  // the officer is no longer looking at.
  useEffect(() => {
    if (focus?.node?.kind === "fir") setTarget({ label: nodeLabel(focus.node), payload: nodeTarget(focus.node) });
    else if (!focus) setTarget(null);
  }, [focus]);
  useEffect(() => { outRef.current?.scrollTo({ top: outRef.current.scrollHeight }); }, [lines, open, small]);

  const say = useCallback((entry) => setLines((ls) => [...ls.slice(-59), { id: `${Date.now()}-${Math.random()}`, ...entry }]), []);
  const agents = pack?.agents || [];
  const card = (id) => agents.find((a) => a.id === id);
  const nameOf = (id) => card(id)?.name || id;

  // ── notifying the officer ────────────────────────────────────────────────────
  const notify = useCallback((title, text) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((ts) => [...ts.slice(-2), { id, title, text }]);
    setTimeout(() => setToasts((ts) => ts.filter((t) => t.id !== id)), 8000);
    if (!prefs.current.seen) setUnread((n) => n + 1);
    // Off by default: the browser prompt is the officer's to trigger (`notify on`).
    if (prefs.current.system && document.hidden && typeof Notification !== "undefined" && Notification.permission === "granted") {
      try { new Notification(`Antar · ${title}`, { body: text }); } catch { /* the in-app notice is already up */ }
    }
  }, []);

  // ── remembering ──────────────────────────────────────────────────────────────
  // Returns what was remembered for this agent on this record before, if anything.
  const remember = useCallback((r, payload, label) => {
    if (!["ok", "empty"].includes(r.status)) return null;   // a refusal or a failure is not a finding
    const key = memKey(payload);
    const prev = memory.current.find((m) => m.agent === r.agent && m.key === key) || null;
    memory.current = [...memory.current.filter((m) => !(m.agent === r.agent && m.key === key)),
                      { agent: r.agent, key, label, payload, status: r.status, cls: r.evidence_class, bottom: r.bottom_line, ts: Date.now() }]
      .slice(-MEM_MAX);
    try { sessionStorage.setItem(MEM_KEY, JSON.stringify(memory.current)); } catch { /* memory then lasts until reload */ }
    return prev;
  }, []);

  const post = useCallback((msg) => {              // a message one agent sent another
    comms.current = [...comms.current.slice(-79), { ts: Date.now(), ...msg }];
    sim.current.queue.push(msg);
  }, []);

  // ── running an agent, and agents talking ─────────────────────────────────────
  const runAgent = useCallback(async (id, payload, given, via = null) => {
    // Name the record by what THIS agent works on: Geo dropped on a FIR is running on the
    // FIR's district, and saying "Geo on <accused id>" would read as mapping a person.
    const needs = pack?.agents?.find((a) => a.id === id)?.needs;
    const label = (payload && typeof payload === "object" && (
      needs === "station" ? payload.station : needs === "district" ? (payload.district || payload.station)
        : needs === "crime type" ? [payload.crime_group, payload.district].filter(Boolean).join(" · ") : payload.accused)) || given;
    setBusy((b) => [...b, id]);
    let r;
    try {
      r = await fetchAPI("/api/console/run", { method: "POST", body: JSON.stringify({ agent: id, target: payload }) });
    } catch (e) {
      say({ kind: "err", text: e.status === 404
        ? "The console is not available on this backend yet. Restart the backend to load it."
        : `The ${id} agent could not be reached (${e.message}).` });
      setBusy((b) => b.filter((x) => x !== id));
      return;
    }
    setBusy((b) => b.filter((x) => x !== id));
    lastRun.current = r;
    const prev = remember(r, payload, label);
    const seen = prev ? { at: prev.ts, same: prev.bottom === r.bottom_line } : null;
    say({ kind: "result", r, label: label || r.target, via, seen });

    if (seen && !seen.same) notify(`${r.name} on ${label}: answer changed`, `${r.bottom_line} (was, at ${clock(seen.at)}: ${prev.bottom})`);
    else if (!prefs.current.seen) notify(`${r.name || id} on ${label}`, r.bottom_line);

    if (via) {                                      // this run WAS the reply to another agent
      post({ from: id, to: via, text: short(r.bottom_line) || `${label}: done, the answer is in the terminal.` });
      return;
    }
    // Hand the record to the agent this one recommends, and let it answer. Its target is
    // the one named in the recommendation, or the same record when none is named.
    const next = (r.next || []).map((n) => /^run (\w+)\s*(.*)$/.exec(n)).find((m) => m && m[1] !== id && ICON[m[1]]);
    if (!next || !prefs.current.auto || !["ok", "refused"].includes(r.status)) return;
    const to = next[1], typed = next[2].trim();
    post({ from: id, to, text: r.status === "refused"
      ? `${label} is not mine to run. Take it.`
      : (short(r.bottom_line) ? `${r.bottom_line} Check it from your side.` : `${label} is ready. Check it from your side.`) });
    runAgent(to, typed || payload, typed || label, id);
  }, [say, remember, notify, post, pack]);

  const exec = useCallback((raw) => {
    const text = raw.trim();
    if (!text) return;
    say({ kind: "in", text });
    const [word, ...rest] = text.split(/\s+/);
    // A leading slash is accepted, as in the chat box: /help is help.
    const cmd = word.toLowerCase().replace(/^\//, ""), arg = rest.join(" ");
    // The three modes Antar has in chat, as terminal commands. Each is a name for work the
    // console already does, so nothing new runs behind them:
    //   think        scan the records in view (Fast Run)
    //   connect      who and what a record is tied to (Network, then Linkage)
    //   anticipate   what to expect at a place (Forecast for a station, Geo for a district)
    if (cmd === "think") { onThink?.(); say({ kind: "sys", text: "Think: scanning the records in this view. The findings open when it finishes." }); return; }
    if (cmd === "connect" || cmd === "anticipate") {
      const typed = arg.trim();
      const pl = typed || target?.payload, label = typed || target?.label;
      if (!pl) {
        say({ kind: "err", text: cmd === "connect" ? "Connect what? Click a record, or type an accused id: connect S0041"
                                                    : "Anticipate where? Type a station or a district: anticipate Bellanduru PS" });
        return;
      }
      const name = typeof pl === "string" ? pl : (pl.station || pl.district || pl.accused || "");
      if (cmd === "connect") { runAgent("network", pl, label); runAgent("linkage", pl, label); return; }
      const isPlace = typeof pl === "string" ? !/^(ACC-|S\d)/i.test(pl) : !!(pl.station || pl.district);
      if (!isPlace) { say({ kind: "err", text: "Anticipate works on a place, never a person. Type a station or a district: anticipate Bellanduru PS" }); return; }
      const district = typeof pl === "string" ? / (City|Dist|District|Railways)$/i.test(pl) : !pl.station;
      runAgent(district ? "geo" : "forecast", typeof pl === "string" ? (district ? { district: name } : { station: name }) : pl, label);
      return;
    }
    if (cmd === "clear") { setLines([]); return; }
    if (cmd === "help") {
      const all = pack?.commands || [];
      const want = arg.toLowerCase().split(/\s+/)[0];
      if (!want) {
        say({ kind: "list", title: "Commands", lead: "help <command> shows examples. Tab completes; ↑ and ↓ walk your history.",
              rows: all.map((c) => [c.cmd, c.does]) });
        return;
      }
      const one = all.find((c) => c.cmd.split(" ")[0] === want);
      if (!one) { const g = nearest(want, WORDS); say({ kind: "err", text: `There is no command '${want}'.${g ? ` Did you mean ${g}?` : ""}` }); return; }
      say({ kind: "list", title: one.cmd, lead: one.does, rows: [
        ...(USAGE[want] || [want]).map((x) => ["Example", x]),
        ...(want === "run" || want === "about" ? agents.map((a) => [a.id, `needs a ${a.needs}`]) : []),
      ] });
      return;
    }
    if (cmd === "history") {
      const items = history.current.items;
      say(items.length ? { kind: "list", title: "History", rows: items.slice(-20).map((x, i) => [String(items.length - Math.min(20, items.length) + i + 1), x]) }
                       : { kind: "sys", text: "Nothing has been typed yet." });
      return;
    }
    if (cmd === "agents") { say({ kind: "list", title: "Agents", rows: agents.map((a) => [a.id, `${a.purpose} Needs a ${a.needs}.`]) }); return; }
    if (cmd === "identity") {
      if (!pack || pack.error) { say({ kind: "err", text: "Identity is not loaded. Restart the backend to load the console." }); return; }
      say({ kind: "list", title: `${pack.name} (${pack.meaning})`, lead: pack.role, rows: [
        ...(pack.version ? [["Constitution", `Version ${pack.version}, in force since ${pack.since}. Type evolution for how it has changed with use.`]] : []),
        ...pack.laws.map((l, i) => [`Law ${i + 1}`, `${l.law}. ${l.rule}`]),
        ...pack.thinking.map((s, i) => [`${i + 1} ${s.step}`, s.how]),
        ...pack.usps.map((u) => ["USP", `${u.claim} - ${u.how}.`]),
      ] });
      return;
    }
    if (cmd === "learnings") {
      const L = learned.current;
      if (!L.list.length) { say({ kind: "sys", text: "Nothing has been read from today's records yet. Restart the backend if this stays empty." }); return; }
      say({ kind: "list", title: `What the records show today (${L.date})`, lead: "Each line is a count. Click one on the Brain screen for the rows behind it.",
            rows: L.list.map((l) => [`${nameOf(l.from)} → ${nameOf(l.to)}`, l.text]) });
      return;
    }
    if (cmd === "evolution") {
      // Read when asked, not with the identity pack: these are counts, and they move.
      fetchAPI("/api/console/evolution")
        .then((ev) => say({ kind: "list", title: `How ${ev.name} has changed with use`,
                            lead: "Each line is counted from the store that records it.",
                            rows: ev.record.flatMap((r) => [[r.what, r.value], ["", r.how]]) }))
        .catch((e) => say({ kind: "err", text: e.status === 404
          ? "This backend does not have the evolution record yet. Restart the backend to load it."
          : `The evolution record could not be read (${e.message}).` }));
      return;
    }
    if (cmd === "about") {
      const a = card(arg.toLowerCase());
      if (!a) { say({ kind: "err", text: `There is no agent called '${arg}'. Type agents to list them.` }); return; }
      const mine = memory.current.filter((m) => m.agent === a.id).slice(-1)[0];
      say({ kind: "list", title: a.role.startsWith(a.name) ? a.role : `${a.name} (${a.role})`, lead: `${a.purpose} Needs a ${a.needs}.`, rows: [
        ...a.method.map((m, i) => [`Step ${i + 1}`, m]), ["Refuses", a.refuses],
        ...(a.guardrails.length ? [["Checks", a.guardrails.join(", ")]] : []),
        ...(mine ? [["Last ran", `${clock(mine.ts)} on ${mine.label}: ${mine.bottom}`]] : []),
      ] });
      return;
    }
    if (cmd === "select") {
      if (!arg) { say({ kind: "err", text: "Select what? Example: select S0041" }); return; }
      const inView = controlRef?.current?.find?.(arg);
      if (!inView) setTarget({ label: arg, payload: arg });
      say({ kind: "sys", text: inView ? `Selected ${arg}.` : `Selected ${arg}. It is not drawn in the current view; agents can still run on it.` });
      return;
    }
    if (cmd === "fastrun") { onThink?.(); say({ kind: "sys", text: "Fast Run started on the current view. The findings open when it finishes." }); return; }
    if (cmd === "assemble") { setRoam(false); say({ kind: "sys", text: "Agents are assembling. Type roam to release them." }); return; }
    if (cmd === "roam") { setRoam(true); say({ kind: "sys", text: "Agents released." }); return; }
    if (cmd === "memory") {
      const who = arg.toLowerCase();
      if (who && !ICON[who]) { say({ kind: "err", text: `There is no agent called '${arg}'.` }); return; }
      const rows = memory.current.filter((m) => !who || m.agent === who).slice(who ? -8 : -12).reverse()
        .map((m) => [`${clock(m.ts)} ${nameOf(m.agent)}`, `${m.label}: ${m.bottom}`]);
      say(rows.length ? { kind: "list", title: who ? `What ${nameOf(who)} remembers` : "What the agents remember (this session)", rows }
                      : { kind: "sys", text: who ? `${nameOf(who)} has not run this session.` : "Nothing is remembered yet. Run an agent first." });
      return;
    }
    if (cmd === "forget") {
      memory.current = []; comms.current = [];
      try { sessionStorage.removeItem(MEM_KEY); } catch { /* nothing stored */ }
      say({ kind: "sys", text: "Memory and message log cleared." });
      return;
    }
    if (cmd === "log") {
      const rows = comms.current.slice(-12).map((m) => [`${clock(m.ts)} ${nameOf(m.from)} → ${nameOf(m.to)}`, m.text]);
      say(rows.length ? { kind: "list", title: "Messages between agents", rows } : { kind: "sys", text: "No agent has messaged another yet." });
      return;
    }
    if (cmd === "auto") {
      if (!["on", "off"].includes(arg)) { say({ kind: "sys", text: `Hand-off between agents is ${prefs.current.auto ? "on" : "off"}. Type auto on or auto off.` }); return; }
      prefs.current.auto = arg === "on";
      say({ kind: "sys", text: prefs.current.auto ? "On: an agent hands its record to the next agent, which answers." : "Off: each agent answers alone." });
      return;
    }
    if (cmd === "notify") {
      if (arg === "off") { prefs.current.system = false; say({ kind: "sys", text: "System notifications off. Notices still appear on this screen." }); return; }
      if (arg !== "on") { say({ kind: "sys", text: `System notifications are ${prefs.current.system ? "on" : "off"}. Type notify on or notify off.` }); return; }
      if (typeof Notification === "undefined") { say({ kind: "err", text: "This browser has no system notifications. Notices still appear on this screen." }); return; }
      Notification.requestPermission().then((p) => {
        prefs.current.system = p === "granted";
        say({ kind: "sys", text: p === "granted" ? "On: results are also raised by the system when this tab is in the background."
                                                 : "The browser did not allow notifications. Notices still appear on this screen." });
      });
      return;
    }
    if (cmd === "why") {
      const r = lastRun.current;
      if (!r) { say({ kind: "err", text: "No agent has run yet." }); return; }
      say({ kind: "list", title: `How ${r.name || r.agent} worked on ${r.target || "this record"}`,
            rows: (r.method || []).map((m, i) => [`Step ${i + 1}`, m]) });
      return;
    }
    if (cmd === "run") {
      const [first, ...tgt] = rest;
      if (!first) { say({ kind: "err", text: "Run which agent? Example: run network S0041" }); return; }
      const id = first.toLowerCase(), typed = tgt.join(" ");
      if (typed) { runAgent(id, typed, typed); return; }
      if (target) { runAgent(id, target.payload, target.label); return; }
      // Nothing named and nothing selected: the record this agent last worked, if it has one.
      const last = memory.current.filter((m) => m.agent === id).slice(-1)[0];
      if (!last) { say({ kind: "err", text: `Run ${id} on what? Click a record, drop the agent on one, or type a target.` }); return; }
      say({ kind: "sys", text: `No record given: using ${last.label}, which ${nameOf(id)} last ran at ${clock(last.ts)}.` });
      runAgent(id, last.payload, last.label);
      return;
    }
    const guess = nearest(cmd, WORDS);
    say({ kind: "err", text: `'${word}' is not a command.${guess ? ` Did you mean ${guess}?` : ""} Type help for the list.` });
  }, [agents, pack, target, controlRef, onThink, runAgent, say]); // eslint-disable-line react-hooks/exhaustive-deps

  // One learning, with the working shown: the rows it was counted from, its evidence class
  // and where it was read.
  const showLearning = useCallback((l) => {
    say({ kind: "list", title: l.title, lead: l.text, rows: [
      ...l.rows,
      ["Evidence class", `${l.evidence_class} · ${CLASS_NAME[l.evidence_class] || ""}`],
      ["Read from", l.source],
      ["Passed", `${nameOf(l.from)} → ${nameOf(l.to)}`],
    ] });
  }, [say, pack]); // eslint-disable-line react-hooks/exhaustive-deps

  // What the rest of the Brain screen may ask of the console: run a command as if typed.
  useEffect(() => {
    if (apiRef) apiRef.current = { run: (cmd) => { setOpen(true); setSmall(false); exec(cmd); } };
  });

  // What the terminal offers under the prompt. While the officer types: the commands and
  // agents that complete what is there. With the line empty: what makes sense NOW - the
  // step the last result recommended, the agents that can take the selected record, or,
  // with nothing selected, where to start.
  function offers() {
    const text = input.trimStart(), cmds = pack?.commands || [];
    const does = (w) => cmds.find((c) => c.cmd.split(" ")[0] === w)?.does || "";
    if (text) {
      const parts = text.split(/\s+/), first = parts[0].toLowerCase();
      if (parts.length === 1) return WORDS.filter((w) => w.startsWith(first) && w !== first).slice(0, 6).map((w) => ({ fill: `${w} `, show: w, note: does(w) }));
      if (["run", "about", "memory"].includes(first) && parts.length === 2) {
        return ORDER.filter((id) => id.startsWith(parts[1].toLowerCase()) && id !== parts[1].toLowerCase()).slice(0, 6)
          .map((id) => ({ fill: `${first} ${id} `, show: `${first} ${id}`, note: card(id)?.purpose || "" }));
      }
      if (first === "help" && parts.length === 2) return WORDS.filter((w) => w.startsWith(parts[1].toLowerCase())).slice(0, 6).map((w) => ({ fill: `help ${w}`, show: `help ${w}`, note: does(w) }));
      return [];
    }
    const out = [];
    (lastRun.current?.next || []).filter((n) => /^run \w/.test(n)).slice(0, 2).forEach((n) => out.push({ run: n, show: n, note: "recommended by the last result" }));
    if (target) {
      const pl = target.payload;
      const kind = typeof pl === "string" ? (/^(ACC-|S\d)/i.test(pl) ? "accused" : / PS$/i.test(pl) ? "station" : "district")
        : pl.accused ? "accused" : pl.station ? "station" : pl.district ? "district" : "crime_group";
      (FOR_KIND[kind] || []).forEach((id) => { if (!out.some((o) => o.show.startsWith(`run ${id}`))) out.push({ run: `run ${id}`, show: `run ${id}`, note: `on ${target.label}` }); });
    } else {
      out.push({ run: "learnings", show: "learnings", note: "what the records show today" },
               { run: "agents", show: "agents", note: "who can do what" },
               { run: "fastrun", show: "fastrun", note: "scan this view" });
    }
    if (!out.some((o) => o.show === "help")) out.push({ run: "help", show: "help", note: "every command" });
    return out.slice(0, 5);
  }

  function onKey(e) {
    const h = history.current;
    // The keys a terminal answers to: Ctrl+L clears the screen, Ctrl+C or Esc drops the line.
    if (e.ctrlKey && e.key.toLowerCase() === "l") { e.preventDefault(); setLines([]); return; }
    if ((e.ctrlKey && e.key.toLowerCase() === "c" && !window.getSelection()?.toString()) || e.key === "Escape") {
      if (input) { e.preventDefault(); say({ kind: "in", text: `${input}^C` }); setInput(""); }
      return;
    }
    if (e.key === "Enter") {
      if (input.trim()) { h.items.push(input.trim()); h.at = h.items.length; }
      exec(input); setInput("");
    } else if (e.key === "ArrowUp" && h.items.length) {
      e.preventDefault(); h.at = Math.max(0, h.at - 1); setInput(h.items[h.at] || "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault(); h.at = Math.min(h.items.length, h.at + 1); setInput(h.items[h.at] || "");
    } else if (e.key === "Tab") {
      e.preventDefault();                            // Tab takes the first offer, as a shell would
      const first = offers()[0];
      if (first) setInput(first.fill || `${first.run} `);
    }
  }

  // ── movement ─────────────────────────────────────────────────────────────────
  // One requestAnimationFrame loop steers all nine agents by writing styles directly: no
  // React render happens per frame. An agent accelerates toward a point, slows as it
  // arrives, keeps its distance from the others, and is pushed out of every control panel
  // - so it is always somewhere the officer can see it and never parked under a panel.
  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    const S = sim.current;
    const rnd = (a, b) => a + Math.random() * (b - a);
    const ease = (t) => { const k = Math.max(0, Math.min(1, t)); return k * k * (3 - 2 * k); };
    let walls = [], wallsAt = 0;
    const measure = (now) => {
      wallsAt = now;
      const box = layer.getBoundingClientRect(), pad = 30;
      const rects = [...(layer.parentElement?.children || [])]
        .filter((el) => el !== layer && el.tagName !== "STYLE" && !/bsx-(netwrap|orbits|hint)/.test(el.className || ""))
        .concat(winRef.current ? [winRef.current] : [])
        .map((el) => el.getBoundingClientRect())
        .filter((r) => r.width > 0 && r.height > 0 && r.width * r.height < box.width * box.height * 0.6);
      walls = rects.map((r) => ({ l: r.left - box.left - pad, t: r.top - box.top - pad, r: r.right - box.left + pad, b: r.bottom - box.top + pad }));
    };
    const blocked = (x, y) => walls.some((w) => x > w.l && x < w.r && y > w.t && y < w.b);
    const freeSpot = (W, H) => {
      for (let k = 0; k < 24; k++) {
        const x = rnd(38, W - 38), y = rnd(60, H - 84);
        if (!blocked(x, y)) return [x, y];
      }
      return [W / 2, H / 2];
    };
    measure(performance.now());
    ORDER.forEach((id, i) => {
      if (S.a[id]) return;
      const [x, y] = freeSpot(layer.clientWidth, layer.clientHeight);
      S.a[id] = { x, y, vx: 0, vy: 0, tx: x, ty: y, arrived: true, wait: performance.now() + 400 + i * 300, held: false };
    });
    let raf = 0, prev = performance.now();
    const frame = (now) => {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.05, (now - prev) / 1000); prev = now;
      if (prefs.current.drawn === false) return;      // not on screen: nothing to move
      const W = layer.clientWidth, H = layer.clientHeight;
      if (now - wallsAt > 1200) measure(now);
      // the line the agents hold when assembled: the row with the fewest places under a panel
      const gap = Math.min(APART, (W - 80) / (ORDER.length - 1));
      const slotX = (i) => W / 2 + (i - (ORDER.length - 1) / 2) * gap;
      const lineY = prefs.current.roam ? 0 : [H - 96, H / 2, 110]
        .map((y) => [y, ORDER.filter((_, i) => blocked(slotX(i), y)).length]).sort((a, b) => a[1] - b[1])[0][0];

      // Fast Run flight. Two rings round the middle of the brain, turning opposite ways.
      // Each agent has a place on a ring and follows it; the place starts where the agent
      // already is - its own angle and distance carry over and ease onto the ring - so
      // nothing jumps when the flight starts, and the turn speeds up and slows down rather
      // than switching on and off.
      const F = S.fly;
      if (F) {
        if (!F.p) {
          const cx = W / 2, cy = H / 2, rx = Math.min(W * 0.28, 340), ry = Math.min(H * 0.3, 230);
          F.geo = { cx, cy, rx, ry }; F.p = {};
          const polar = ORDER.filter((id) => S.a[id]).map((id) => {
            const u = (S.a[id].x - cx) / rx, v = (S.a[id].y - cy) / ry;
            return { id, ang: Math.atan2(v, u), rad: Math.hypot(u, v) };
          }).sort((p, q) => p.ang - q.ang);
          // The agents nearest the middle take the inner ring, so nobody crosses the
          // brain to reach a place. On a ring, two agents that start close together are
          // eased apart just far enough not to overlap - no further.
          [...polar].sort((p, q) => p.rad - q.rad).forEach((p, k) => { p.outer = k >= Math.floor(polar.length / 2); p.to = p.ang; });
          for (const outer of [true, false]) {
            const ring = polar.filter((p) => p.outer === outer), gap = outer ? 0.5 : 0.72;
            for (let pass = 0; pass < 40 && ring.length > 1; pass++) {
              ring.forEach((p, j) => {
                const q = ring[(j + 1) % ring.length];
                const d = ((q.to - p.to) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
                if (d < gap) { p.to -= (gap - d) / 2; q.to += (gap - d) / 2; }
              });
            }
          }
          polar.forEach((p, k) => {
            F.p[p.id] = { ang0: p.ang, turn: p.to - p.ang, rad0: p.rad, ring: p.outer ? 1 : 0.58, spin: p.outer ? 1.5 : -2, k };
          });
          [...(orbitRef.current?.children || [])].forEach((el, j) => {
            el.setAttribute("cx", cx); el.setAttribute("cy", cy);
            el.setAttribute("rx", rx * (j ? 0.58 : 1)); el.setAttribute("ry", ry * (j ? 0.58 : 1));
          });
        }
        F.e = (now - F.t0) / 1000;
        F.theta += dt * ease(F.e / 0.9) * (F.stopAt ? 1 - ease((now - F.stopAt) / 700) : 1);
        if (F.stopAt && now - F.stopAt > 700) {       // landed: carry on roaming from here
          ORDER.forEach((id) => { const a = S.a[id]; if (a) { a.tx = a.x; a.ty = a.y; a.arrived = true; a.wait = now + rnd(1200, 4200); } });
          S.fly = null;
        }
      }

      ORDER.forEach((id, i) => {
        const a = S.a[id], el = bugEls.current[id];
        if (!a || !el) return;
        const fp = S.fly?.p?.[id];
        if (a.held) { a.vx = a.vy = 0; }
        else if (fp) {
          const { cx, cy, rx, ry } = S.fly.geo, on = ease(S.fly.e / 1.1);
          const ang = fp.ang0 + fp.turn * on + fp.spin * S.fly.theta;
          const rad = (fp.rad0 + (fp.ring - fp.rad0) * on) * (1 + 0.06 * on * Math.sin(S.fly.e * 2.4 + fp.k));
          // Follow the place rather than sit on it: speed builds and fades with the
          // distance still to cover, two agents that come close give way, and nothing
          // moves faster than the eye can track.
          let wx = (Math.max(34, Math.min(W - 34, cx + rx * rad * Math.cos(ang))) - a.x) * FLY_PULL;
          let wy = (Math.max(50, Math.min(H - 72, cy + ry * rad * Math.sin(ang))) - a.y) * FLY_PULL;
          for (const o of ORDER) {
            const q = S.a[o];
            if (o === id || !q) continue;
            const ex = a.x - q.x, ey = a.y - q.y, e = Math.hypot(ex, ey);
            if (e > 0 && e < 58) { wx += (ex / e) * (58 - e) * 14; wy += (ey / e) * (58 - e) * 14; }
          }
          const sp = Math.hypot(wx, wy), k = sp > FLY_MAX ? FLY_MAX / sp : 1;
          a.vx = wx * k; a.vy = wy * k;
          a.x += a.vx * dt; a.y += a.vy * dt;
        }
        else {
          if (!prefs.current.roam) { a.tx = slotX(i); a.ty = lineY; a.arrived = false; }
          else if (blocked(a.tx, a.ty)) [a.tx, a.ty] = freeSpot(W, H);       // a panel opened over the goal
          else if (Math.hypot(a.tx - a.x, a.ty - a.y) < 6) {
            if (!a.arrived) { a.arrived = true; a.wait = now + rnd(3000, 8000); }    // hold position a while
            else if (now > a.wait) { [a.tx, a.ty] = freeSpot(W, H); a.arrived = false; }
          }
          let dx = a.tx - a.x, dy = a.ty - a.y;
          const d = Math.hypot(dx, dy) || 1;
          const want = Math.min(SPEED, d * 1.7);                               // ease in to the goal
          let wx = (dx / d) * want, wy = (dy / d) * want;
          for (const o of ORDER) {                                             // keep clear of each other
            const q = S.a[o];
            if (o === id || !q) continue;
            const ex = a.x - q.x, ey = a.y - q.y, e = Math.hypot(ex, ey);
            if (e > 0 && e < APART) { wx += (ex / e) * (APART - e) * 2.4; wy += (ey / e) * (APART - e) * 2.4; }
          }
          for (const w of walls) {                                             // and out from under panels
            if (a.x > w.l && a.x < w.r && a.y > w.t && a.y < w.b) {
              const out = [[a.x - w.l, -1, 0], [w.r - a.x, 1, 0], [a.y - w.t, 0, -1], [w.b - a.y, 0, 1]].sort((p, q) => p[0] - q[0])[0];
              wx += out[1] * SPEED * 1.6; wy += out[2] * SPEED * 1.6;
            }
          }
          const ax = wx - a.vx, ay = wy - a.vy, am = Math.hypot(ax, ay) || 1, cap = Math.min(am, ACCEL * dt);
          a.vx += (ax / am) * cap; a.vy += (ay / am) * cap;
          a.x = Math.max(34, Math.min(W - 34, a.x + a.vx * dt));
          a.y = Math.max(50, Math.min(H - 72, a.y + a.vy * dt));
        }
        const hover = a.held ? 0 : Math.sin(now / 620 + i * 1.7) * 2.2;       // never perfectly still
        el.style.transform = `translate(${(a.x - 22).toFixed(1)}px, ${(a.y - 22 + hover).toFixed(1)}px)`;
        el.style.setProperty("--lean", `${Math.max(-9, Math.min(9, a.vx * 0.14)).toFixed(1)}deg`);
      });

      // the carried agent says what it is over
      const held = S.held && S.a[S.held], hint = hintRef.current;
      if (hint) {
        if (held && S.moved) {
          const box = layer.getBoundingClientRect();
          const n = controlRef?.current?.nodeAt?.(held.x + box.left, held.y + box.top);
          hint.textContent = n ? `Run on ${nodeLabel(n)}` : "Drop on a record to run";
          hint.dataset.hit = n ? "1" : "";
          hint.style.transform = `translate(${(held.x + 30).toFixed(0)}px, ${(held.y - 12).toFixed(0)}px)`;
          hint.style.opacity = "1";
        } else hint.style.opacity = "0";
      }
      // a message in flight: a line between the two agents and a packet travelling along it
      const t = S.talk, bubble = sayRef.current, wire = wireRef.current, packet = packetRef.current;
      if (t && S.a[t.from] && bubble) {
        const p = S.a[t.from], q = S.a[t.to], k = ((now - t.t0) % 1100) / 1100;
        const left = Math.max(8, Math.min(W - bubble.offsetWidth - 8, p.x - bubble.offsetWidth / 2));
        bubble.style.transform = `translate(${left.toFixed(0)}px, ${Math.max(8, p.y - 50).toFixed(0)}px)`;
        if (q && wire && packet) {                    // agent to agent; a line to the officer has no wire
          wire.setAttribute("x1", p.x); wire.setAttribute("y1", p.y); wire.setAttribute("x2", q.x); wire.setAttribute("y2", q.y);
          // Three packets a third of the way apart, each fading in as it leaves the sender
          // and out as it reaches the listener, so the direction reads at a glance.
          [packet, packet2Ref.current, packet3Ref.current].forEach((el, j) => {
            if (!el) return;
            const kj = (k + j / 3) % 1;
            el.setAttribute("cx", p.x + (q.x - p.x) * kj); el.setAttribute("cy", p.y + (q.y - p.y) * kj);
            el.setAttribute("opacity", Math.sin(Math.PI * kj).toFixed(2));
          });
        }
      }
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [controlRef]);

  // The line on screen - only when there is something to say. A message one agent really
  // sent another goes first. Otherwise, now and then, an agent points the officer at
  // something counted in this view and offers to look into it; each is said once per
  // round, and clicking the line takes the offer. No small talk.
  useEffect(() => {
    const S = sim.current;
    const tick = setInterval(() => {
      const now = Date.now();
      if (S.talk && now < S.talk.until) return;
      let line = S.queue.shift(), hold = 5200;
      const T = tips.current;
      // One round: what the records show today, agent to agent, then what this view offers
      // the officer. Only agents that are drawn can speak.
      const pool = [
        ...learned.current.list.filter((l) => ICON[l.from] && ICON[l.to]).map((l) => ({ from: l.from, to: l.to, text: l.text, learn: l })),
        ...T.list.map((s) => ({ from: s.agent, to: "you", text: `${s.text}. ${s.ask}?`, cmd: s.cmd })),
      ];
      if (!line && prefs.current.drawn !== false && now > S.nextIdle && !document.hidden && pool.length) {
        line = pool[T.at % pool.length];
        T.at += 1;
        hold = 9000;
        // a full round said: stay quiet for a good while before saying them again
        S.nextIdle = now + hold + (T.at % pool.length === 0 ? 90000 : 14000);
      }
      if (!line) { if (S.talk) { S.talk = null; setTalk(null); } return; }
      S.talk = { ...line, t0: performance.now(), until: now + hold };
      if (!line.cmd && !line.learn) S.nextIdle = Math.max(S.nextIdle, now + hold + 12000);
      setTalk({ ...line, key: now, hold });
    }, 600);
    return () => clearInterval(tick);
  }, []);

  // Pick an agent up. A press without movement opens its card; a drop on a record runs it
  // there; a drop anywhere else simply leaves it where it was put.
  function startCarry(e, id) {
    if (e.button !== 0) return;
    const S = sim.current, a = S.a[id], layer = layerRef.current;
    if (!a || !layer) return;
    const box = layer.getBoundingClientRect(), sx = e.clientX, sy = e.clientY;
    a.held = true; S.held = id; S.moved = false;
    const move = (ev) => {
      if (!S.moved && Math.hypot(ev.clientX - sx, ev.clientY - sy) < 6) return;
      if (!S.moved) { S.moved = true; setDragging(id); }
      a.x = ev.clientX - box.left; a.y = ev.clientY - box.top;
    };
    const up = (ev) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      const moved = S.moved;
      a.held = false; S.held = null; S.moved = false; setDragging(null);
      a.tx = a.x; a.ty = a.y; a.arrived = true; a.wait = performance.now() + 6000;
      if (!moved) {
        // A click: with a record selected the agent goes to work on it and answers in the
        // terminal; with nothing selected there is nothing to work on, so it shows its card.
        setOpen(true); setSmall(false);
        if (target) { say({ kind: "in", text: `run ${id} ${target.label}` }); runAgent(id, target.payload, target.label); }
        else exec(`about ${id}`);
        return;
      }
      const n = controlRef?.current?.nodeAt?.(ev.clientX, ev.clientY);
      if (!n) return;
      // The record becomes the terminal's target, but the graph is not zoomed into it:
      // the agents belong to the All Data view, and focusing would take them off screen
      // in the middle of the job. The terminal is not forced open either - with it
      // closed, the answer arrives as a notice.
      setTarget({ label: nodeLabel(n), payload: nodeTarget(n) });
      runAgent(id, nodeTarget(n), nodeLabel(n));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function startMove(e) {
    const win = winRef.current;
    if (!win || e.target.closest("button")) return;
    const box = win.getBoundingClientRect(), dx = e.clientX - box.left, dy = e.clientY - box.top;
    const move = (ev) => {
      win.style.left = `${Math.max(8, Math.min(window.innerWidth - 80, ev.clientX - dx))}px`;
      win.style.top = `${Math.max(70, Math.min(window.innerHeight - 40, ev.clientY - dy))}px`;
      win.style.right = "auto"; win.style.bottom = "auto";
    };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  const openTerminal = () => { setOpen(true); setSmall(false); };

  return (
    <>
      <style>{CSS}</style>

      {/* The agents live in this layer and nowhere else: it is the brain stage, so they
          cannot move over the navigation or leave the screen. */}
      <div ref={layerRef} className={`bt-layer${showAgents ? "" : " off"}${flying ? " fly" : ""}`} style={{ "--c": ACCENT }} aria-hidden={!showAgents}>
        <svg ref={orbitRef} className="bt-orbits" aria-hidden="true"><ellipse /><ellipse /></svg>
        <svg className="bt-wires" aria-hidden="true" style={{ opacity: talk && talk.to !== "you" ? 1 : 0 }}>
          <line ref={wireRef} />
          <circle ref={packetRef} r="3.4" />
          <circle ref={packet2Ref} r="2.8" />
          <circle ref={packet3Ref} r="2.2" />
        </svg>
        {ORDER.map((id) => {
          const a = card(id);
          return (
            <div key={id} ref={(el) => { bugEls.current[id] = el; }}
                 className={`bt-bug${busy.includes(id) || flyAgent === id ? " busy" : ""}${dragging === id ? " held" : ""}${talk?.from === id ? " speaking" : ""}${talk?.to === id ? " hearing" : ""}`}
                 onPointerDown={(e) => startCarry(e, id)} role="button" tabIndex={0} aria-label={a ? `${a.name} agent` : id}
                 onKeyDown={(e) => { if (e.key === "Enter") { openTerminal(); exec(target ? `run ${id}` : `about ${id}`); } }}
                 title={a ? `${a.name}: ${a.purpose} ${target ? `Click to run on ${target.label}.` : "Select a record and click, or drag onto one."}` : id}>
              <i>
                <Mascot className="bt-face" size={FACE_PX} label={a ? `${a.name} agent` : id}
                        directions={`/mascots/${FACE[id]}-directions.webp`} reactions={`/mascots/${FACE[id]}-reactions.webp`} />
                <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d={ICON[id]} /></svg>
              </i>
              <span>{a?.name || id}</span>
            </div>
          );
        })}
        <b ref={hintRef} className="bt-hint" aria-hidden="true" />
        {talk && (
          <p key={talk.key} ref={sayRef} className={`bt-say${talk.cmd || talk.learn ? " ask" : ""}${talk.learn ? " learn" : ""}`} aria-live="off"
             style={{ animationDuration: `${talk.hold || 5200}ms` }}
             title={talk.cmd ? `Click to ${talk.cmd}` : talk.learn ? "Click for the rows behind this" : undefined}
             onClick={talk.cmd || talk.learn ? () => {
               openTerminal();
               if (talk.learn) showLearning(talk.learn); else exec(talk.cmd);
               sim.current.talk = null; setTalk(null);
             } : undefined}>
            {talk.learn && <i>{kn ? "ಇಂದು" : "Today"}</i>}
            <b>{nameOf(talk.from)} → {talk.to === "you" ? "You" : nameOf(talk.to)}</b>{talk.text}
          </p>
        )}
      </div>

      {showConsole && (
        <div className="bt-pills">
          <button className={`bsx-pill bt-pill${open ? " on" : ""}`} onClick={() => { setOpen((v) => !v); setSmall(false); }}
                  title={kn ? "ಬ್ರೈನ್ ಟರ್ಮಿನಲ್" : "Brain terminal"} aria-label="Brain terminal" aria-pressed={open}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 5h16v14H4zM8 10l3 2-3 2M13 15h3" /></svg>
            {kn ? "ಟರ್ಮಿನಲ್" : "Terminal"}
            {unread > 0 && <em aria-label={`${unread} new`}>{unread}</em>}
          </button>
          {/* The same switch as the terminal's assemble / roam: one press lines the agents up, the next lets them go. */}
          {showAgents && (
            <button className={`bsx-pill bt-pill bt-asm${roam ? "" : " on"}`} onClick={() => setRoam((v) => !v)} aria-pressed={!roam}
                    title={roam ? (kn ? "ಏಜೆಂಟ್‌ಗಳನ್ನು ಸಾಲಾಗಿ ನಿಲ್ಲಿಸಿ" : "Assemble the agents") : (kn ? "ಏಜೆಂಟ್‌ಗಳನ್ನು ಬಿಡಿ" : "Release the agents")}
                    aria-label={roam ? "Assemble the agents" : "Release the agents"}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="2.2" /><circle cx="12" cy="12" r="2.2" /><circle cx="19" cy="12" r="2.2" /></svg>
            </button>
          )}
        </div>
      )}

      {showConsole && (
        <div className="bt-toasts" role="status" aria-live="polite">
          {toasts.map((t) => (
            <button key={t.id} onClick={() => { openTerminal(); setToasts((ts) => ts.filter((x) => x.id !== t.id)); }}>
              <b>{t.title}</b><span>{t.text}</span>
            </button>
          ))}
        </div>
      )}

      {open && showConsole && (
        <section ref={winRef} className={`bt-win${small ? " small" : ""}`} aria-label="Brain terminal">
          <header onPointerDown={startMove}>
            <b>{pack?.name ? `${pack.name.toUpperCase()} · ` : ""}BRAIN TERMINAL</b>
            <span className="bt-tgt" title="Selected record">{target ? target.label : (kn ? "ದಾಖಲೆ ಆಯ್ಕೆಯಾಗಿಲ್ಲ" : "no record selected")}</span>
            <button onClick={() => setSmall((v) => !v)} aria-label={small ? "Expand" : "Minimise"}>{small ? "▢" : "–"}</button>
            <button onClick={() => setOpen(false)} aria-label="Close">×</button>
          </header>
          {!small && (
            <>
              <div ref={outRef} className="bt-out" onClick={() => { if (!window.getSelection()?.toString()) inRef.current?.focus(); }}>
                {pack?.error && <p className="bt-err">The console backend did not answer. Restart the backend to load it.</p>}
                {!lines.length && (
                  <p className="bt-sys">Antar brain terminal. Drag an agent onto a record, or type a command: the line under the prompt
                    shows what fits right now. <u onClick={() => exec("help")}>help</u> lists everything, Tab completes, ↑ recalls.</p>
                )}
                {lines.map((l) => <Line key={l.id} l={l} onRun={exec} nameOf={nameOf} />)}
                {busy.length > 0 && <p className="bt-sys bt-busy">{busy.map(nameOf).join(" and ")} {busy.length > 1 ? "are" : "is"} working…</p>}
              </div>
              {(() => {
                const list = offers();
                if (!list.length) return null;
                return (
                  <div className="bt-offers" role="listbox" aria-label={input.trim() ? "Completions" : "Suggested commands"}>
                    <em>{input.trim() ? "tab" : (kn ? "ಸಲಹೆ" : "try")}</em>
                    {list.map((o) => (
                      <button key={o.show} role="option" aria-selected="false" title={o.note}
                              onClick={() => { if (o.run) { history.current.items.push(o.run); history.current.at = history.current.items.length; exec(o.run); setInput(""); } else setInput(o.fill); inRef.current?.focus(); }}>
                        <b>{o.show}</b>{o.note && <span>{o.note}</span>}
                      </button>
                    ))}
                  </div>
                );
              })()}
              <div className="bt-in">
                <span>antar@brain{target ? <i> [{target.label}]</i> : null} ›</span>
                <input ref={inRef} autoFocus value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKey}
                       placeholder={target ? "run network" : "help"} spellCheck={false} autoComplete="off" autoCapitalize="off" aria-label="Command" />
              </div>
            </>
          )}
        </section>
      )}
    </>
  );
}

function Line({ l, onRun, nameOf }) {
  if (l.kind === "in") return <p className="bt-cmd"><span>antar@brain ›</span> {l.text}</p>;
  if (l.kind === "sys") return <p className="bt-sys">{l.text}</p>;
  if (l.kind === "err") return <p className="bt-err">{l.text}</p>;
  if (l.kind === "list") {
    return (
      <div className="bt-list">
        <b>{l.title}</b>
        {l.lead && <p>{l.lead}</p>}
        <dl>{l.rows.map(([k, v], i) => (<div key={i}><dt>{k}</dt><dd>{v}</dd></div>))}</dl>
      </div>
    );
  }
  const r = l.r;
  return (
    <article className={`bt-res ${r.status}`}>
      <header>
        <b>{r.name || r.agent}</b>
        <span>{l.label}</span>
        {r.evidence_class && <i className={`bt-cls ${r.evidence_class}`} title={CLASS_NAME[r.evidence_class]}>{r.evidence_class} · {CLASS_NAME[r.evidence_class]}</i>}
        {r.status === "refused" && <i className="bt-cls R">not run</i>}
        {r.ms != null && r.status !== "refused" && <em>{r.cached ? "cached" : `${r.ms} ms`}</em>}
      </header>
      {l.via && <p className="bt-via">Asked by {nameOf(l.via)}</p>}
      <p className="bt-bl">{r.bottom_line}</p>
      {r.context && <p className="bt-cx">{r.context}</p>}
      {r.evidence?.length > 0 && <ul>{r.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>}
      {(r.limits || []).map((x, i) => <p key={i} className="bt-lim">Note: {x}</p>)}
      {l.seen && <p className={`bt-seen${l.seen.same ? "" : " changed"}`}>{l.seen.same ? `Same answer as at ${clock(l.seen.at)}.` : `Changed since ${clock(l.seen.at)}.`}</p>}
      {r.next?.length > 0 && (
        <footer>{r.next.map((n, i) => (/^run \w/.test(n)
          ? <button key={i} onClick={() => onRun(n)}>{n}</button>
          : <span key={i}>Next: {n}</span>))}</footer>
      )}
    </article>
  );
}

const CSS = `
/* Beside the search box, clear of the Fast Run pill on the right. */
.bt-pills { position: absolute; top: 16px; left: 336px; z-index: 9; display: flex; align-items: center; gap: 6px; }
.bsx-pill.bt-pill { position: static; opacity: 1; color: #A5F3FC; background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.05); }
/* Assemble: a mark, no word - three agents in a line. */
.bsx-pill.bt-asm { padding: 8px 9px; }
.bsx-pill.bt-pill:hover, .bsx-pill.bt-pill.on { border-color: rgba(34,230,240,.45); color: #fff; }
.bsx-pill.bt-pill em { font: 700 9.5px 'JetBrains Mono', monospace; font-style: normal; color: #06121B; background: #22E6F0; border-radius: 999px; padding: 0 5px; min-width: 15px; text-align: center; }
@media (max-width: 1080px) { .bt-pills { left: auto; right: 16px; top: 104px; } }

/* Above the control panels (z-index 7): the agents steer around them, and are never hidden by one. */
.bt-layer { --c: #22E6F0; position: absolute; inset: 0; z-index: 8; overflow: hidden; pointer-events: none; transition: opacity .25s ease; }
/* Off the All Data view the agents are not there at all: not drawn, not clickable. */
.bt-layer.off { opacity: 0; visibility: hidden; }
.bt-layer.off .bt-bug > i, .bt-layer.off .bt-bug > span { pointer-events: none; }
.bt-wires { position: absolute; inset: 0; width: 100%; height: 100%; transition: opacity .3s; }
/* Fast Run: the two rings the agents fly, drawn only while they are flying. */
.bt-orbits { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; transition: opacity .5s ease; }
.bt-layer.fly .bt-orbits { opacity: 1; }
.bt-orbits ellipse { fill: none; stroke: var(--c); stroke-width: 1; stroke-dasharray: 3 9; opacity: .32; animation: bt-dash 2.4s linear infinite; }
.bt-orbits ellipse + ellipse { animation-direction: reverse; opacity: .22; }
@keyframes bt-dash { to { stroke-dashoffset: -48; } }
.bt-layer.fly .bt-bug { opacity: 1; }
.bt-layer.fly .bt-bug > i { box-shadow: 0 0 0 7px rgba(3,6,12,.78), 0 0 0 9px rgba(34,230,240,.2), 0 0 22px var(--c); }
.bt-layer.fly .bt-bug > i::before { animation-duration: 1.6s; border-color: rgba(34,230,240,.7); border-left-color: transparent; border-right-color: transparent; }
/* A message in flight: the wire runs toward the listener, the packets travel along it. */
.bt-wires line { stroke: var(--c); stroke-width: 1.4; stroke-dasharray: 3 7; opacity: .75; filter: drop-shadow(0 0 4px var(--c)); animation: bt-flow .7s linear infinite; }
.bt-wires circle { fill: #fff; filter: drop-shadow(0 0 6px var(--c)); }
@keyframes bt-flow { to { stroke-dashoffset: -20; } }
/* The listener answers the packets with a ring that opens outward; the speaker's ring tightens. */
.bt-bug.hearing > i { animation: bt-recv 1.1s ease-out infinite; }
.bt-bug.speaking > i::before { animation-duration: 2.2s; border-color: rgba(34,230,240,.85); border-left-color: transparent; border-right-color: transparent; }
@keyframes bt-recv { 0% { box-shadow: 0 0 0 7px rgba(3,6,12,.78), 0 0 0 7px rgba(34,230,240,.55), 0 0 16px rgba(34,230,240,.4); }
  100% { box-shadow: 0 0 0 7px rgba(3,6,12,.78), 0 0 0 20px rgba(34,230,240,0), 0 0 16px rgba(34,230,240,.4); } }

/* Present but quiet: an agent sits a little back while it only moves, and comes up to full
   strength when it talks, is spoken to, is working, is carried, or is pointed at. */
.bt-bug { position: absolute; left: 0; top: 0; width: 44px; height: 44px; pointer-events: none; will-change: transform, opacity; user-select: none; touch-action: none;
  opacity: .82; transition: opacity .25s ease; }
.bt-bug:hover, .bt-bug:focus-visible, .bt-bug.speaking, .bt-bug.hearing, .bt-bug.busy, .bt-bug.held { opacity: 1; }
.bt-bug > i, .bt-bug > span { pointer-events: auto; cursor: grab; }
/* The body: a dark disc the character stands on, leaning into its direction of travel,
   inside a slow scan ring. The disc and the halo round it are near-black: the graph behind
   is a field of bright dots, and on a pale disc the agents were lost among them. */
.bt-bug > i { position: absolute; left: 4px; top: 4px; width: 36px; height: 36px; border-radius: 50%; color: var(--c);
  background: radial-gradient(circle at 50% 30%, #16233A 0%, #070C16 72%); border: 1.5px solid var(--c);
  box-shadow: 0 0 0 7px rgba(3,6,12,.78), 0 0 16px rgba(34,230,240,.38), 0 6px 14px rgba(0,0,0,.6); transform: rotate(var(--lean, 0deg)); transition: box-shadow .2s, scale .2s; }
.bt-bug > i::before { content: ""; position: absolute; inset: -5px; border-radius: 50%; border: 1px dashed rgba(34,230,240,.4); border-left-color: transparent; border-right-color: transparent; animation: bt-spin 9s linear infinite; }
.bt-bug > i::after { content: ""; position: absolute; right: 0; top: 0; width: 5px; height: 5px; border-radius: 50%; background: var(--c); box-shadow: 0 0 6px var(--c); animation: bt-led 2.4s ease-in-out infinite; }
/* The character. page-mascot sets its own inline box, so the placement here has to win:
   the head (centred at about 50% / 42% of a sprite cell) sits on the middle of the disc. */
.bt-bug .bt-face { position: absolute !important; left: 50%; top: 50%; margin: ${-Math.round(FACE_PX * 0.44)}px 0 0 ${-FACE_PX / 2}px; cursor: grab !important; outline: none;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
.bt-bug.held .bt-face { cursor: grabbing !important; }
/* What the agent does, as a badge on the disc. */
.bt-bug > i > svg { position: absolute; right: -6px; bottom: -4px; box-sizing: content-box; padding: 2px; border-radius: 50%; background: rgba(6,11,18,.94); border: 1px solid var(--c); }
.bt-bug > span { position: absolute; left: 50%; top: 45px; transform: translateX(-50%); font: 600 8.5px 'JetBrains Mono', monospace; letter-spacing: .04em; text-transform: uppercase; color: #CFFAFE;
  background: rgba(3,6,12,.94); border: 1px solid rgba(34,230,240,.22); padding: 1px 6px; border-radius: 4px; white-space: nowrap; }
.bt-bug:hover > i, .bt-bug.speaking > i { box-shadow: 0 0 0 7px rgba(3,6,12,.78), 0 0 0 9px rgba(34,230,240,.3), 0 0 20px var(--c); }
.bt-bug.held > i { cursor: grabbing; scale: 1.14; box-shadow: 0 0 0 7px rgba(3,6,12,.78), 0 0 0 10px rgba(34,230,240,.34), 0 0 24px var(--c); }
.bt-bug.busy > i::before { border-style: solid; border-color: var(--c) transparent transparent transparent; animation-duration: .9s; }
.bt-bug.speaking > i::after, .bt-bug.busy > i::after { animation-duration: .5s; }
@keyframes bt-spin { to { transform: rotate(360deg); } }
@keyframes bt-led { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }

.bt-hint { position: absolute; left: 0; top: 0; opacity: 0; transition: opacity .15s; font: 600 10.5px 'JetBrains Mono', monospace; color: #94A3B8;
  background: rgba(6,11,18,.92); padding: 3px 7px; border-radius: 6px; white-space: nowrap; border: 1px solid rgba(255,255,255,.1); }
.bt-hint[data-hit="1"] { color: #fff; border-color: #22E6F0; }
.bt-say { position: absolute; left: 0; top: 0; margin: 0; max-width: min(640px, 82vw); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font: 11px 'Inter', sans-serif; color: #E2E8F0; background: rgba(6,11,18,.94); border: 1px solid rgba(34,230,240,.45);
  border-radius: 999px; padding: 3px 10px; animation: bt-type 5.2s ease both; }
.bt-say.ask { pointer-events: auto; cursor: pointer; }
/* A line about today's records carries a small mark, so it is not read as an offer. */
.bt-say i { font: 600 9px 'JetBrains Mono', monospace; font-style: normal; letter-spacing: .08em; text-transform: uppercase; color: #06121B; background: var(--c); border-radius: 999px; padding: 1px 6px; margin-right: 7px; }
.bt-say.learn { border-color: rgba(34,230,240,.7); box-shadow: 0 6px 22px rgba(0,0,0,.55); }
.bt-say.ask:hover { border-color: #22E6F0; color: #fff; }
.bt-say b { font: 600 9.5px 'JetBrains Mono', monospace; color: var(--c); margin-right: 7px; letter-spacing: .03em; }
@keyframes bt-type { 0% { clip-path: inset(0 100% 0 0); opacity: 1; } 22% { clip-path: inset(0 0 0 0); } 88% { opacity: 1; } 100% { clip-path: inset(0 0 0 0); opacity: 0; } }

.bt-toasts { position: fixed; right: 20px; bottom: 20px; z-index: 960; display: flex; flex-direction: column; gap: 8px; align-items: flex-end; pointer-events: none; }
.bt-toasts button { pointer-events: auto; cursor: pointer; text-align: left; width: min(340px, 86vw); display: flex; flex-direction: column; gap: 3px; padding: 9px 12px; border-radius: 10px;
  background: rgba(6,11,18,.96); border: 1px solid rgba(34,230,240,.35); border-left: 3px solid #22E6F0; box-shadow: 0 10px 30px rgba(0,0,0,.6); animation: bt-rise .25s ease both; }
.bt-toasts b { font: 600 10.5px 'JetBrains Mono', monospace; color: #22E6F0; letter-spacing: .03em; }
.bt-toasts span { font: 12px/1.45 'Inter', sans-serif; color: #E2E8F0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
@keyframes bt-rise { from { opacity: 0; transform: translateY(8px); } }

/* Opens wide enough to read a result without resizing: about 980 by 410, centred. */
.bt-win { position: fixed; left: max(8px, calc(50% - min(490px, 46vw))); bottom: 64px; z-index: 950; width: min(980px, 92vw); height: 410px; min-width: 300px; min-height: 200px; max-width: 92vw; max-height: 78vh;
  display: flex; flex-direction: column; resize: both; overflow: hidden; border-radius: 10px; background: rgba(6,11,18,.96);
  border: 1px solid rgba(34,230,240,.28); box-shadow: 0 14px 44px rgba(0,0,0,.7); font-family: 'JetBrains Mono', monospace; color: #E2E8F0; }
.bt-win.small { height: auto; min-height: 0; resize: none; }
.bt-win > header { display: flex; align-items: center; gap: 8px; padding: 7px 10px; background: rgba(34,230,240,.08); border-bottom: 1px solid rgba(34,230,240,.18); cursor: move; user-select: none; flex-shrink: 0; }
.bt-win > header b { font-size: 10.5px; letter-spacing: .06em; color: #22E6F0; white-space: nowrap; }
.bt-tgt { flex: 1; min-width: 0; font-size: 10px; color: #94A3B8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: right; }
.bt-win > header button { background: none; border: 0; color: #94A3B8; cursor: pointer; font-size: 14px; line-height: 1; padding: 0 3px; }
.bt-win > header button:hover { color: #fff; }
.bt-out { flex: 1; min-height: 0; overflow-y: auto; padding: 9px 11px; display: flex; flex-direction: column; gap: 7px; font-size: 11px; line-height: 1.5; scrollbar-width: thin; }
.bt-out p { margin: 0; }
.bt-cmd { color: #fff; } .bt-cmd span { color: #22E6F0; }
.bt-sys { color: #94A3B8; } .bt-sys u { color: #22E6F0; cursor: pointer; text-decoration: none; }
.bt-busy { color: #22E6F0; }
.bt-err { color: #FBBF24; }
.bt-list b { color: #22E6F0; font-size: 11px; } .bt-list p { color: #CBD5E1; margin: 2px 0 4px; }
.bt-list dl { margin: 3px 0 0; display: flex; flex-direction: column; gap: 2px; }
.bt-list dl div { display: grid; grid-template-columns: 132px 1fr; gap: 8px; }
.bt-list dt { color: #94A3B8; } .bt-list dd { margin: 0; color: #E2E8F0; font-family: 'Inter', sans-serif; }
.bt-res { border-left: 2px solid #22E6F0; padding: 2px 0 2px 9px; display: flex; flex-direction: column; gap: 4px; }
.bt-res.refused { border-left-color: #FBBF24; } .bt-res.error { border-left-color: #F87171; }
.bt-res > header { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.bt-res > header b { color: #22E6F0; text-transform: uppercase; font-size: 10.5px; letter-spacing: .05em; }
.bt-res > header span { color: #94A3B8; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 150px; }
.bt-res > header em { margin-left: auto; font-style: normal; font-size: 9.5px; color: #64748B; }
.bt-cls { font-style: normal; font-size: 9.5px; padding: 1px 6px; border-radius: 999px; border: 1px solid currentColor; }
.bt-cls.K { color: #34D399; } .bt-cls.D { color: #60A5FA; } .bt-cls.I { color: #FB923C; } .bt-cls.U { color: #94A3B8; } .bt-cls.R { color: #FBBF24; }
.bt-via { font-size: 10px; color: #64748B; }
.bt-bl { font: 600 12.5px/1.45 'Inter', sans-serif; color: #fff; }
.bt-cx { font: 11.5px/1.45 'Inter', sans-serif; color: #CBD5E1; }
.bt-res ul { margin: 0; padding-left: 15px; font: 11px/1.5 'Inter', sans-serif; color: #CBD5E1; }
.bt-lim { font: 10.5px/1.45 'Inter', sans-serif; color: #94A3B8; }
.bt-seen { font-size: 10px; color: #64748B; } .bt-seen.changed { color: #FBBF24; }
.bt-res footer { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.bt-res footer button { font: 10px 'JetBrains Mono', monospace; color: #22E6F0; background: rgba(34,230,240,.07); border: 1px solid rgba(34,230,240,.3); border-radius: 999px; padding: 2px 8px; cursor: pointer; }
.bt-res footer button:hover { background: rgba(34,230,240,.16); }
.bt-res footer span { font: 10.5px 'Inter', sans-serif; color: #94A3B8; }
.bt-in { display: flex; align-items: center; gap: 7px; padding: 7px 11px; border-top: 1px solid rgba(255,255,255,.09); flex-shrink: 0; }
.bt-in span { color: #22E6F0; font-size: 11px; font-weight: 700; white-space: nowrap; }
.bt-in span i { font-style: normal; font-weight: 500; color: #94A3B8; }
.bt-in input { caret-color: #22E6F0; }
/* What fits right now, or what completes the line: one row above the prompt. */
.bt-offers { display: flex; align-items: center; gap: 6px; padding: 5px 11px; border-top: 1px solid rgba(255,255,255,.07); overflow-x: auto; scrollbar-width: none; flex-shrink: 0; }
.bt-offers::-webkit-scrollbar { display: none; }
.bt-offers em { font: 600 9px 'JetBrains Mono', monospace; font-style: normal; letter-spacing: .08em; text-transform: uppercase; color: #64748B; flex: none; }
.bt-offers button { flex: none; display: inline-flex; align-items: baseline; gap: 7px; padding: 2px 9px; border-radius: 6px; border: 1px solid rgba(255,255,255,.1); background: rgba(255,255,255,.03); cursor: pointer; }
.bt-offers button:first-of-type { border-color: rgba(34,230,240,.4); }
.bt-offers button:hover { border-color: #22E6F0; background: rgba(34,230,240,.08); }
.bt-offers b { font: 500 11px 'JetBrains Mono', monospace; color: #E2E8F0; }
.bt-offers span { font: 10.5px 'Inter', sans-serif; color: #64748B; max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bt-in input { flex: 1; min-width: 0; background: transparent; border: 0; outline: none; color: #fff; font: 12px 'JetBrains Mono', monospace; }
/* ── A quieter terminal ──
   One accent, used sparingly: the prompt and what can be clicked. Everything read at
   length is soft grey-white at normal weight, nothing is in capitals, and a result is set
   apart by space rather than by a coloured rail and a row of outlined badges. */
.bt-win { background: rgba(8,12,20,.97); border-color: rgba(255,255,255,.1); box-shadow: 0 14px 40px rgba(0,0,0,.6); }
.bt-win > header { background: transparent; border-bottom-color: rgba(255,255,255,.07); }
.bt-win > header b { color: #94A3B8; font-weight: 500; letter-spacing: .04em; }
.bt-out { gap: 12px; padding: 12px 14px; font-size: 11.5px; line-height: 1.6; }
.bt-cmd { color: #CBD5E1; } .bt-cmd span { color: #5B7083; font-weight: 400; }
.bt-sys, .bt-via, .bt-seen { color: #6B7A8D; }
.bt-err { color: #D9B66A; }
.bt-res { border-left: 1px solid rgba(255,255,255,.1); padding: 0 0 0 12px; gap: 3px; }
.bt-res.refused, .bt-res.error { border-left-color: rgba(255,255,255,.1); }
.bt-res > header { gap: 8px; }
.bt-res > header b { color: #8FD3DA; text-transform: none; font-weight: 500; font-size: 11px; letter-spacing: 0; }
.bt-res > header span { color: #6B7A8D; max-width: 220px; }
.bt-res > header em { color: #4E5C6E; }
.bt-cls { border: 0; padding: 0; font-size: 10.5px; opacity: .85; }
.bt-bl { font: 400 12.5px/1.55 'Inter', sans-serif; color: #E2E8F0; }
.bt-res.refused .bt-bl, .bt-res.empty .bt-bl { color: #A9B6C6; }
.bt-cx, .bt-res ul { color: #9AA8B9; font-size: 11.5px; }
.bt-lim { color: #6B7A8D; }
.bt-res footer button { background: none; border: 0; padding: 0; color: #8FD3DA; font-size: 10.5px; }
.bt-res footer button:hover { background: none; text-decoration: underline; }
.bt-list b { color: #8FD3DA; font-weight: 500; } .bt-list p { color: #A9B6C6; }
.bt-list dt { color: #6B7A8D; } .bt-list dd { color: #CBD5E1; }
.bt-offers { gap: 14px; padding: 6px 14px; border-top-color: rgba(255,255,255,.06); }
.bt-offers em { color: #4E5C6E; }
.bt-offers button, .bt-offers button:first-of-type { border: 0; background: none; padding: 0; gap: 6px; }
.bt-offers button:hover { background: none; }
.bt-offers b { color: #A9B6C6; font-weight: 400; } .bt-offers button:first-of-type b { color: #8FD3DA; }
.bt-offers button:hover b { color: #fff; }
.bt-offers span { color: #4E5C6E; }
.bt-in { padding: 9px 14px; border-top-color: rgba(255,255,255,.06); }
.bt-in span { color: #8FD3DA; font-weight: 500; } .bt-in span i { color: #6B7A8D; }
.bt-in input { color: #E2E8F0; }
@media (prefers-reduced-motion: reduce) { .bt-say, .bt-bug > i::before, .bt-bug > i::after, .bt-orbits ellipse, .bt-wires line, .bt-bug.hearing > i { animation: none; } }
`;
