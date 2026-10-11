import { ADMIN_ID, ADMIN_ROLE } from "./auth";

// Hardcoded for production to prevent local environment variables from overriding it
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "");

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

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

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

