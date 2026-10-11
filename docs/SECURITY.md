# Antar — Security Architecture

> **TEAM VIMARAKSHA** — *"Predict and Secure Before the Threat Materializes."*
> Antar converts 10,00,000+ FIR records into structured pattern intelligence and unknown
> leads. Those records name victims, witnesses and suspects. The same discipline we apply
> to crime — anticipate the pattern, act before the incident — is applied here to the
> system itself.

This document is the contract. Every control listed as **Done** has a test in
`tests/test_rag_security.py` or `tests/test_security_hardening.py`. Anything not yet
done is listed as **Partial** or **Roadmap**, with no rounding up.

References: [OWASP RAG Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html) ·
[Pluralsight — How to secure RAG applications](https://www.pluralsight.com/resources/blog/ai-and-data/how-to-secure-rag-applications-AI)

---

## 1. Threat model

| # | Threat | How it reaches Antar | Primary control |
|---|---|---|---|
| T1 | **Information disclosure through errors** | An exception's text (file paths, DB names, the QuickML endpoint URL and project id, upstream error bodies, tokens) returned in a 500, an SSE `error` event or a reasoning trail | `app/core/security.py`: generic message + `error_id`, full detail logged server-side only |
| T2 | **Indirect prompt injection** | Instruction-shaped text inside an MO narrative, an uploaded CSV, an OCR'd scan, an OSINT page or a stored session, which is then retrieved into a prompt | `app/core/rag_security.py`: normalise → detect → fence → reinforce → canary |
| T3 | **Corpus / index poisoning** | Unauthenticated CSV upload into the FIR registry; officers' questions embedded into the Second Brain and retrieved into *other* officers' prompts | Admin-only ingestion, row/chunk quarantine, SHA-256 provenance |
| T4 | **Identity spoofing** | `X-Role: Admin` header accepted from anyone | Signed-token mode (`ANTAR_AUTH_SECRET`), one identity resolver, gateway fails closed |
| T5 | **Cross-officer data access** | Listing/loading another officer's encrypted saved conversation; reading another officer's profile | Owner-bound session envelope; self-or-Admin rule |
| T6 | **System-prompt / policy exfiltration** | "Repeat your instructions" via the question or via a poisoned record | Per-process canary; output blocked if echoed; deterministic fallback |
| T7 | **PII egress to the model provider** | Phone, Aadhaar, email, PAN in prompts to QuickML | `redact_pii` on every LLM path (the vision and logprob paths previously skipped it) |
| T8 | **Abuse / DoS** | Rotating spoofed `X-Forwarded-For`, unbounded limiter table, oversized bodies | Proxy-hop-aware client IP, LRU-bounded buckets, request-body ceiling |
| T9 | **Secret sprawl** | `.session_key` committed to git; `.env` and session data not excluded from `catalyst deploy` | Untracked, ignored in `.gitignore` / `.catalystignore` / `.appignore` |

---

## 2. Error hygiene (T1)

**Rule: a caller never sees exception text.** They see a plain sentence and a reference:

```json
{"detail": "Something went wrong on our side. (ref ERR-3F9A1C22D0)", "error_id": "ERR-3F9A1C22D0"}
```

The full exception, with traceback, is logged under the same `ERR-…` id, so support can
find it from a screenshot.

| Layer | Behaviour |
|---|---|
| Unhandled exception | Global handler returns the generic body above. |
| `HTTPException` ≥ 500 | Detail replaced by the generic message (structured `{"preparing": …}` 503s are ours and are kept, scrubbed). |
| `HTTPException` 4xx | Detail kept (it is written for the officer) but passed through `scrub_text`. |
| Validation (422) | Only `loc`, `msg`, `type` — Pydantic's echo of the offending **input** is dropped (it can be a victim's name or phone number). |
| SSE stream | `error` event carries `message` + `error_id` only. |
| Reasoning trails, job summaries, HITL records, orchestrator status, obs traces | `public_message()` or `scrub_text()` at the source. |

`scrub_text()` removes Windows/UNC/Unix paths, URLs, `host:port`, traceback frames,
bearer tokens, Zoho `1000.x.y` tokens, JWTs, long hex blobs and any `key=value` whose key
names a secret.

Also in `security.install()`: `X-Content-Type-Options`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, COOP/CORP, `Permissions-Policy`, `Cache-Control: no-store`
on `/api/*` (case data never sits in a browser or proxy cache), a strict CSP on JSON
responses, HSTS in production, and a request-body ceiling (`ANTAR_MAX_BODY_MB`).
`/docs`, `/redoc` and `/openapi.json` are **off in production**.

---

## 3. RAG security — OWASP cheat-sheet mapping

### 3.1 Document poisoning & ingestion

| OWASP control | Status | Where |
|---|---|---|
| Scan for injection markers, hidden instructions, invisible Unicode | **Done** | `rag_security.normalize_untrusted`, `detect_injection` |
| Quarantine rather than index suspicious chunks | **Done** | `second_brain/ingestion._admit` — all five index writers |
| Hash every chunk (SHA-256) and record provenance | **Done** | `meta.sha256`, `meta.source`, `meta.ingested_at` |
| Restrict write access to authorised ingestion | **Done** | `/api/upload` and `/api/brain/seed` are Admin-only; `/api/upload` rate-limited |
| Row-level screening of bulk uploads | **Done** | `services/ingestion.map_and_ingest_csv` → `records_quarantined` |
| Approval workflow before new data goes live | Roadmap | Route CSV ingestion through `app/core/hitl.py` (the separation-of-duties engine already exists). |
| Verify hash before retrieval | Roadmap | Store the hash durably with the embedding (Catalyst Data Store) and re-check on load. |

Normalisation keeps Kannada intact: ZWJ/ZWNJ are only removed when not adjacent to an
Indic script character, because Kannada conjuncts depend on them.

### 3.2 Context window & prompt injection

| OWASP control | Status | Where |
|---|---|---|
| Delimit retrieved content as untrusted | **Done** | `fence()` — random per-call id, so a record cannot forge the closing tag; literal tags inside content defanged |
| Reinforce system instructions **after** retrieved content | **Done** | `fence()` appends a reminder after every block |
| Do not rely on system-prompt position alone | **Done** | Policy in the system prompt (`harden_system`) **and** after data **and** output checks |
| Scan retrieved chunks for "SYSTEM:", "ignore previous" … | **Done** | `fence()` detects and neutralises instruction-shaped spans |
| Limit retrieved chunks | **Done (pre-existing)** | `_slim_rows_for_compose` caps at 3–25 rows; Brain recall `k=3`–5 |

Fenced call sites: compose (FIR rows), multi-agent synthesis (agent context), translate,
forensic OCR (investigator notes; the image itself is governed by the hardened vision
system prompt).

**Architectural advantage:** Antar never lets the model write SQL. Questions map to
whitelisted templates (T1–T23) with validated parameters, so an injected instruction
cannot become a database query. The deterministic answer writer means that when an LLM
output is blocked, the officer still gets a correct, record-backed answer.

### 3.3 Output validation

| OWASP control | Status | Where |
|---|---|---|
| Validate every model output before it is returned | **Done** | `check_output()` inside `quickml_generate`, vision and logprob paths |
| Detect system-prompt leakage | **Done** | Per-process canary; echo → `OutputBlocked` → caller's deterministic fallback, no retry |
| Redact secrets / credentials / paths in output | **Done** | `check_output` (line-wise, so markdown tables survive) |
| Numbers and identifiers must exist in evidence | **Done (pre-existing)** | `answer_guardrails` G1/G3 |
| PII redaction on the way to the model | **Done** | Aadhaar, phone, **email, PAN** (new); case/FIR/vehicle ids preserved |
| Redact dynamically by the viewer's access level | Roadmap | Needs field classification on FIR columns. |

### 3.4 Access control, isolation, caching

| OWASP control | Status | Notes |
|---|---|---|
| Identity for every query | **Partial** | One resolver (`resolve_identity`). Header mode is a **demo**; signed mode is real. |
| Pre-retrieval filtering by jurisdiction / classification | Roadmap | Chunks already carry `station_code`; filter by the officer's posting once identity is verified. |
| Response cache scoped by user/permission | Roadmap | `product_store` caches aggregate views (no per-record PII) — audit before caching anything record-level. |
| Log every retrieval with identity | **Partial** | The audit middleware records officer, role, path and status for every `/api/*` call; chunk ids per retrieval are in obs traces, not yet in the audit chain. |

### 3.5 Monitoring & red-team in CI

- Quarantines, context injections and blocked outputs are logged under
  `antar.rag_security` and counted (`rag_security.counters()`).
- `tests/test_rag_security.py` is the red-team suite that CI runs: poisoned-document
  surfacing, indirect injection, delimiter spoofing, canary leak, invisible-Unicode
  smuggling, and a **benign FIR prose** set that must *not* be flagged (false positives
  would silently drop real evidence from the Brain).

---

## 4. Identity (T4, T5)

| Mode | When | Behaviour |
|---|---|---|
| `header` | `ANTAR_AUTH_SECRET` empty (tests, and a developer who has not set one) | Officer and role from `X-Officer` / `X-Role`. **Anyone can claim any role.** The startup log prints a SECURITY warning, and `/api/auth/login` refuses to issue anything. |
| `signed` | `ANTAR_AUTH_SECRET` set (**the build as of 2026-10-12**) | Every call to `/api/*`, `/trace`, `/trust` and `/report/*` needs `Authorization: Bearer <token>`: HMAC-SHA256 over `{sub, role, iat, exp}`, compared in constant time. The only exceptions are `/api/health`, `/api/auth/login` and the two cron endpoints (which take the cron secret). `X-Role`/`X-Officer` are ignored. HITL decisions, hypothesis confirmations, session ownership and the audit log all use the token identity. |

### Sign-in

`POST /api/auth/login {user_id, password}` checks the password and returns the token; the
frontend keeps it in `sessionStorage` and attaches it to every backend request (`lib/auth.js`).

| Property | How |
|---|---|
| No password is stored | Salted scrypt hashes only (`app/core/accounts.py`), written by `scripts/set_password.py` to `auth_users.json` (git- and docker-ignored) or supplied as `ANTAR_USERS` in a container |
| No default account | With no accounts configured nobody can sign in, and the startup log says so |
| An attacker cannot list ids | A wrong password and an unknown id get the same answer, after the same hashing work |
| Guessing is slow | Five failures lock the id for five minutes; the route is rate-limited per address as well |
| A stolen role header is worthless | The role comes from the token, never from a header or the browser session |
| An expired session is visible | The gateway's 401 carries the CORS origin, so the browser sees a refusal (not a network error) and returns the officer to sign-in |

Measured on 2026-10-12 against the running backend: before, 75 of 79 parameter-free GET
routes answered with no identity at all and `X-Role: Admin` opened the audit log; after,
79 of 80 refuse and only `/api/health` answers.

Mint a token by hand (scripts, cron-like jobs): `ANTAR_AUTH_SECRET=… python scripts/mint_token.py U-7001 Admin`.

Also fixed while unifying identity: the AI-reasoning audit ledger read a header nobody
sends (`x-officer-id`), so every entry was attributed to `OF-1001`; `/api/brain/ingest_session`
let the caller set their own `officer_role` as a query parameter; hypothesis confirm/reject
took officer and role from the request body.

Cron endpoints compare the secret in constant time and, **in production, refuse** the
shipped default and the `.env.example` placeholder.

---

## 5. Production checklist

```text
[ ] ANTAR_ENV=production            (docs off, HSTS on, weak cron secrets refused)
[ ] ANTAR_AUTH_SECRET=<48+ random>
[ ] ANTAR_USERS=<output of: python scripts/set_password.py --show-env>   (accounts; hashes only)
[ ] CRON_SECRET_KEY=<32+ random>
[ ] ANTAR_SESSION_KEY=<Fernet key>  (not the generated .session_key file)
[ ] ALLOWED_ORIGINS = exact frontend origin(s), never *
[ ] ANTAR_TRUSTED_PROXY_HOPS matches the real proxy chain (AppSail = 1)
[ ] Startup log shows no "SECURITY:" warnings
[ ] Rotate .session_key — it was committed to git history (see §7)
```

---

## 6. Incident response (RAG-specific)

1. **Poisoned record found** — search logs for `rag_quarantine` / `rag_injection_in_context`
   by `sha256`; remove the source row; rebuild the Brain index (`brain_index.rebuild`) —
   cached products for the affected district should be invalidated (`product_store.invalidate`).
2. **Prompt-leak block** (`rag_output_blocked`) — the answer already fell back to the
   deterministic path. Find the trace by time; identify the retrieved rows in its prompt.
3. **Officer reports an error** — they quote `ERR-…`; grep the server log for it.
4. **Suspected identity abuse** — the audit chain records officer, role, method, path and
   status for every call; in signed mode identities are unforgeable.

---

## 7. Known gaps — next, in order

1. ~~Wire real authentication.~~ **Done 2026-10-12** - see §4, Sign-in. What that leaves:
   - The token sits in `sessionStorage`, so a script-injection bug in the frontend could
     read it. An `HttpOnly` cookie would close that, at the cost of CSRF handling.
   - A token cannot be revoked before it expires (8 hours). Signing out forgets it in the
     browser only. Rotating `ANTAR_AUTH_SECRET` ends every session at once.
   - `/report/{session_id}` is open to any signed-in officer who knows the session id; it
     is not yet bound to the officer who owns the session.
   - Both Docker images still run as root. Add a non-root `USER` once an image can be
     built and tested (the app writes only under `/tmp` on AppSail).
2. **Rotate the session key and purge it from history.** `.session_key` was committed
   (`f6b8906`). It is now untracked and ignored; no remote exists yet, so rotate
   **before the first push** and rewrite history (`git filter-repo --path .session_key --invert-paths`).
3. **Untrack runtime data**: `data_sessions/obs/obs_spans.jsonl` (redacted prompts),
   `data_feedback.jsonl`, `data_sessions/*.enc`.
4. **Jurisdiction-aware retrieval** (pre-retrieval filter on `station_code`).
5. **Ingestion approval** through HITL, and durable per-chunk hashes verified at load.
6. **Rate limit per identity** (not only per IP) once identity is verified.
7. **Dependency scanning** (`pip-audit`, `npm audit`) in CI, pinned embedding-model revisions.
