// Sign-in and the session.
//
//   U-7001  Admin     Operations officer - works cases and PROPOSES real-world actions
//                     (patrol redeployment, watchlist adds).
//   U-9001  Approver  Supervising officer - REVIEWS and decides those actions.
//
// The backend checks the password (POST /api/auth/login) and returns a signed token; every
// other route refuses a call without it. The backend also enforces the split between the
// two accounts (app/core/hitl.py): proposer and approver roles are disjoint, and nobody
// can decide their own proposal. The role shown in this tab is a label - what a call may
// do is decided from the token, on the server.
//
// The token lives in sessionStorage: it goes when the tab closes, and it expires on the
// server after one shift whether or not the tab is still open.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export const ACCOUNTS = {
  "U-7001": { role: "Admin", name: "Operations Officer", home: "/antar" },
  "U-9001": { role: "Approver", name: "Supervising Officer", home: "/approvals" },
};

// Kept for existing imports: the operations account.
export const ADMIN_ID = "U-7001";
export const ADMIN_ROLE = "Admin";
export const APPROVER_ID = "U-9001";
export const APPROVER_ROLE = "Approver";
const SESSION_KEY = "antar_session";

function normId(id) {
  return String(id || "").trim().toUpperCase();
}

export function accountFor(id) {
  return ACCOUNTS[normId(id)] || null;
}

// Back-compat name: now true for ANY known account, not just the admin.
export function isAdminId(id) {
  return !!accountFor(id);
}

// Where an officer lands after signing in.
export function homeFor(role) {
  return role === APPROVER_ROLE ? "/approvals" : "/antar";
}

// A session is one the server issued and has not yet expired. Whether the token is still
// good is the server's call: a 401 on any request ends the session (see below).
export function isValidSession(session) {
  return !!(session && session.officer && session.role && session.token
            && (!session.exp || session.exp * 1000 > Date.now()));
}

export function isApprover(session) {
  return isValidSession(session) && session.role === APPROVER_ROLE;
}

export function readSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null"); } catch { return null; }
}

export function clearSession() {
  // Signing out ends the session on the server too, so a copy of the token stops working.
  // Forgotten here first; the request is best-effort (the token may already have expired).
  let token = null;
  try { token = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null")?.token || null; } catch {}
  try { sessionStorage.removeItem(SESSION_KEY); } catch {}
  if (token && typeof fetch === "function") {
    try {
      fetch(`${API_BASE}/api/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, keepalive: true }).catch(() => {});
    } catch {}
  }
}

// Ask the server to sign this officer in. Resolves to the session; rejects with an Error
// carrying `status` (401 wrong id or password, 429 locked, 503 not configured, 0 unreachable).
export async function signIn(id, password) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: normId(id), password }),
    });
  } catch {
    throw Object.assign(new Error("unreachable"), { status: 0 });
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(typeof body.detail === "string" ? body.detail : "refused"), { status: res.status });
  const session = { officer: body.officer, role: body.role, name: body.name, token: body.token, exp: body.expires_at, ts: Date.now() };
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(session)); } catch {}
  return session;
}

// A printed report is a page of its own, and a new tab cannot carry the token. So it is
// fetched here, with the token, and the tab is pointed at the result. The tab is opened
// first, inside the click, because a window opened after an await is blocked as a pop-up.
export async function openReport(path) {
  const tab = window.open("", "_blank");
  try {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(String(res.status));
    const url = URL.createObjectURL(new Blob([await res.text()], { type: "text/html" }));
    if (tab) tab.location.replace(url); else window.open(url, "_blank");
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    if (tab) tab.close();
  }
}

// ── every call to the backend carries the token ─────────────────────────────────
// The screens call the API from many places, most of them with a bare fetch(). Rather
// than depend on each one remembering the header, fetch itself adds it for requests to
// the backend - and only to the backend, so the token is never sent to a map-tile server
// or a font host. A 401 means the token is missing, expired or no longer accepted: the
// session ends and the officer is returned to the sign-in page.
// Installed when this module loads, which is before any screen's first request.
const GUARDED = /^\/(api\/|trace|trust|report\/)/;

function backendPath(input) {
  try {
    const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
    const origin = API_BASE ? new URL(API_BASE, window.location.href).origin : window.location.origin;
    return url.origin === origin && GUARDED.test(url.pathname) ? url.pathname : null;
  } catch { return null; }
}

if (typeof window !== "undefined" && !window.__antarFetch) {
  const plain = window.fetch.bind(window);
  window.__antarFetch = plain;
  window.fetch = async (input, init = {}) => {
    const path = backendPath(input);
    if (!path) return plain(input, init);
    const headers = new Headers(init.headers || (typeof input !== "string" && input.headers) || {});
    const session = readSession();
    if (session?.token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${session.token}`);
    const res = await plain(input, { ...init, headers });
    if (res.status === 401 && !path.startsWith("/api/auth/login")) {
      clearSession();
      if (!window.location.pathname.startsWith("/login")) window.location.assign("/login");
    }
    return res;
  };
}
