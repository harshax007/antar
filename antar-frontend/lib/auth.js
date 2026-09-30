// Two-account build.
//
//   U-7001  Admin     Operations officer - works cases and PROPOSES real-world actions
//                     (patrol redeployment, watchlist adds).
//   U-9001  Approver  Supervising officer - REVIEWS and decides those actions.
//
// The backend enforces the split (app/core/hitl.py): proposer and approver roles are
// disjoint, and nobody can decide their own proposal. Catalyst Auth is not wired yet, so
// this is a demo gate, not real authentication - the password is not checked and the
// session lives in sessionStorage.

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

export function isValidSession(session) {
  const acct = session && accountFor(session.officer);
  return !!acct && session.role === acct.role;
}

export function isApprover(session) {
  return isValidSession(session) && session.role === APPROVER_ROLE;
}

export function readSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null"); } catch { return null; }
}

export function writeSessionFor(id) {
  const officer = normId(id);
  const acct = accountFor(officer);
  if (!acct) return null;
  const session = { officer, role: acct.role, ts: Date.now() };
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(session)); } catch {}
  return session;
}

export function writeAdminSession() {
  return writeSessionFor(ADMIN_ID);
}

export function clearSession() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch {}
}
