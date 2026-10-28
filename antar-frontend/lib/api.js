import { ADMIN_ID, ADMIN_ROLE } from "./auth";
import { isWakingFailure, markUp, waitForServer } from "./serverStatus";

// Hardcoded for production to prevent local environment variables from overriding it
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000");

export async function fetchAPI(endpoint, options = {}) {
  const headers = new Headers(options.headers || {});
  
  // Fallback identity when no session exists; real requests carry the signed-in account (lib/auth.js).
  let role = ADMIN_ROLE;
  let officer = ADMIN_ID;
  
  let token = null;

  if (typeof window !== "undefined") {
    try {
      const session = JSON.parse(sessionStorage.getItem("antar_session") || "{}");
      if (session.role) role = session.role;
      if (session.officer) officer = session.officer;
      if (session.token) token = session.token;
    } catch {}
  }
  
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("X-Role")) {
    headers.set("X-Role", role);
  }
  if (!headers.has("X-Officer")) {
    headers.set("X-Officer", officer);
  }
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // A server still warming up fails with a network error or a 502/503/504. Wait for it
  // (one shared poll, see lib/serverStatus.js) and ask once more, instead of failing.
  const go = () => fetch(`${API_URL}${endpoint}`, { ...options, headers });
  let response;
  try {
    response = await go();
    if (isWakingFailure(response) && !options.signal?.aborted && await waitForServer()) response = await go();
  } catch (e) {
    if (!isWakingFailure(e) || options.signal?.aborted || !(await waitForServer())) throw wakingError(e);
    try { response = await go(); } catch (e2) { throw wakingError(e2); }
  }
  if (isWakingFailure(response)) throw wakingError(null, response.status);
  markUp();

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    // `detail` is a string for most errors but an OBJECT for structured ones (e.g. the
    // hypothesis confirm gate's 409 carries the full adversarial rebuttal). Passing an
    // object to `new Error` yields "[object Object]", so pull a readable message out and
    // keep the structured payload on the error for callers that want it.
    const d = errorData.detail;
    const message =
      typeof d === "string" ? d
        : (d && (d.message || d.error)) || `API Error: ${response.status}`;
    const err = new Error(message);
    err.status = response.status;
    err.detail = d;
    throw err;
  }

  // Handle empty responses
  if (response.status === 204) {
    return null;
  }

  return response.json();
}


// What a caller sees when the server never came up: said as waking, never as "offline".
function wakingError(cause, status) {
  if (cause && !isWakingFailure(cause)) return cause;
  const err = new Error("Antar is still waking up on the server. Try again in a moment.");
  err.waking = true;
  if (status) err.status = status;
  return err;
}
