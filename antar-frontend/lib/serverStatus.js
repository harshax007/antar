// Is the Antar server there yet?
//
// The server takes a minute or two to warm up after it starts (and a cloud host may be
// cold-starting it). During that time a call fails with a network error or a 502/503/504.
// That is not "offline": it is Antar waking up, and the right thing to do is wait for it
// and try again, while telling the officer what is happening. One shared poll of
// /api/health (it needs no sign-in) serves every caller, so twenty failing calls do not
// start twenty polls.

// same base as lib/api.js; not imported from there, because api.js imports this file
const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000");

const listeners = new Set();
let status = "unknown";          // "unknown" | "up" | "waking"
let waiting = null;              // the one poll in flight, shared by every caller

const WAKING_HTTP = new Set([502, 503, 504]);

export function getServerStatus() { return status; }

function set(next) {
  if (next === status) return;
  status = next;
  listeners.forEach((fn) => { try { fn(next); } catch {} });
}

export function onServerStatus(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// A failed fetch that means "the server is not there yet", as opposed to an answer the
// server gave (a 401, a 404, a 500 with a reason): only those are worth waiting out.
export function isWakingFailure(errOrResponse) {
  if (!errOrResponse) return false;
  if (typeof errOrResponse.status === "number" && "ok" in errOrResponse) return WAKING_HTTP.has(errOrResponse.status);
  if (errOrResponse.name === "AbortError") return false;
  return errOrResponse.name === "TypeError" || errOrResponse.waking === true;
}

export function markUp() { set("up"); }
export function markWaking() { set("waking"); }

async function ping() {
  try {
    const ctl = typeof AbortController !== "undefined" ? new AbortController() : null;
    const t = ctl ? setTimeout(() => ctl.abort(), 6000) : null;
    const r = await fetch(`${API_URL}/api/health`, { cache: "no-store", signal: ctl?.signal });
    if (t) clearTimeout(t);
    return !WAKING_HTTP.has(r.status);       // any real answer, even a refusal, means it is up
  } catch {
    return false;
  }
}

// Resolves true once the server answers, false if it has not within `maxMs`.
export function waitForServer(maxMs = 120000) {
  if (waiting) return waiting;
  markWaking();
  waiting = (async () => {
    const until = Date.now() + maxMs;
    let gap = 1500;
    while (Date.now() < until) {
      if (await ping()) { markUp(); return true; }
      await new Promise((res) => setTimeout(res, gap));
      gap = Math.min(gap * 1.5, 5000);
    }
    return false;
  })().finally(() => { waiting = null; });
  return waiting;
}

// Called once when the app opens: find out early, so the banner is up before the officer
// asks anything rather than after their first question fails.
export async function checkServerOnce() {
  if (await ping()) { markUp(); return true; }
  return waitForServer();
}
