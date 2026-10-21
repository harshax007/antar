# 🎯 ANTAR — Final Demo Pitch Material · 8-MINUTE VERSION

> **Team Vimaraksha · Datathon 2026 · Final Day In-Person Demo**
> Slot: **8 minutes** · Speaker talks, Driver types · Everything below matches the current build

---

## PITCH STRUCTURE OVERVIEW

| Section | Weight | Time (8 min) | Clock | Goal |
|---------|--------|--------------|-------|------|
| **WHY** | 20% | 1 min 36 s | 0:00 – 1:36 | How we *read* the problem — our insight, not the problem statement |
| **HOW** | 30% | 2 min 24 s | 1:36 – 4:00 | Our approach and *why it wins* |
| **WHAT** | 50% | 4 min | 4:00 – 8:00 | Live demo — real questions, real numbers |

> [!NOTE]
> **Facts updated from the draft** — say these, not the old ones:
> 10,00,000 FIRs · **41 districts · 1,155 police stations · 2,365 suspects** · 113 crime types · **26** whitelisted question templates · typical answer **2.8 seconds** (median) · "Yellappa" is the alias of **Raju K. (S0001)**: 6 priors, 8 linked cases, 2 districts.
> Removed because they are not in the build: Section 65B / BSA compliance, DPDP toggles, "98.4% clean rate", map time slider.

---

# ═══════════════════════════════════════════════════════════
# SECTION 1: START WITH WHY (20% · 1 min 36 s)
# ═══════════════════════════════════════════════════════════

> [!IMPORTANT]
> **Do NOT say**: "Crime is a big problem and police need better tools."
> **DO say**: "We sat with the data and found a gap no dashboard fixes."

### 🎤 SPEAKER SCRIPT — WHY

**[0:00 — Hook. Say the number. Then silence.]**

> *"Four lakh twenty-five thousand."*
>
> *"That's how many FIRs are in the Karnataka police data we were given. Forty-one districts. Over a thousand police stations. Twenty-three hundred known suspects."*

**[PAUSE]**

**[0:20 — The real example]**

> *"Take one suspect. Raju K. — known on the street as 'Yellappa'."*
>
> *"Six prior offences. Linked to eight cases — in Rajajinagar, and three hundred kilometres away in Bagalkot. Six people connected to him. One of those Bagalkot FIRs shares his phone."*
>
> *"All of that is already in the data. But to find it, an officer needs days, phone calls between stations, and luck. Because it's **scattered across tables, districts and time**."*

**[1:00 — Our reframe]**

> *"So we stopped thinking 'dashboard'. This isn't a chart problem. It's an **intelligence assembly problem**."*
>
> *"The officer's real question is: **what should I know right now — and can I prove it?** In her own language. In seconds."*
>
> *"That's why we built **Antar**. It thinks, it connects, and it anticipates."*

**[1:36 — Hand-off]** *"Here's how it works."*

### Key Talking Points (WHY)
- **10,00,000 FIRs**, 41 districts, 1,155 stations — real scale
- The problem is **fragmentation**, not visualisation
- Reframe: from "show charts" → **"assemble intelligence and prove it"**
- Real example: **Raju K. alias Yellappa (S0001)** — 8 cases, 2 districts, shared phone
- Plant the tagline: **"Think. Connect. Anticipate."**

---

# ═══════════════════════════════════════════════════════════
# SECTION 2: HOW (30% · 2 min 24 s)
# ═══════════════════════════════════════════════════════════

### 🎤 SPEAKER SCRIPT — HOW

**[1:36 — The idea]**

> *"You don't solve this with one big AI. You solve it with a **team of specialists** — like a real investigation."*
>
> *"When an officer asks something — English or Kannada, typed or spoken — a **Supervisor** decides what kind of question it is, and sends it to the right specialists: the records agent, the network agent, the profile agent, the forecast agent. Then a **Synthesizer** puts it together into one answer. In one to five seconds."*

**[2:15 — Three things that make it different]**

> **"One — it doesn't make up numbers."**
> *"The AI never writes database code. It picks one of thirteen safe, checked question templates. The numbers are counted from real FIRs, and tagged — COMPUTED if we counted it, VERIFIED if it's a record. If something isn't in the data, Antar says 'not on record'. It never invents."*

> **"Two — it speaks the officer's language."**
> *"Ask in Kannada, by voice or text — the answer comes back in Kannada, and it reads it out loud. And the answer comes first: the answer, which way it's moving, then the proof."*

> **"Three — it's ready for a case file."**
> *"Every answer goes into a tamper-proof, hash-chained log. One click turns the session into a sealed PDF report — every question, its method, the FIRs it came from, and a SHA-256 seal."*

**[3:40 — It ships]**

> *"And it runs on CPU only, deployed on Zoho Catalyst. If the cloud AI is slow or down, a circuit breaker switches Antar to its verified path — and it keeps answering."*

**[4:00 — Hand-off]** *"Enough talking. Let's ask it."*

### Key Talking Points (HOW)
- **Supervisor + specialist agents** in a LangGraph graph → Synthesizer
- **13 whitelisted templates** — the AI selects, never writes SQL
- **COMPUTED / VERIFIED tags** on every answer; "not on record" instead of guessing
- **Kannada in, Kannada out** — voice and text
- **Hash-chained audit log** + SHA-256 sealed report
- **CPU-only on Catalyst**, circuit breakers, answers in 1–5 s

---

# ═══════════════════════════════════════════════════════════
# SECTION 3: WHAT — LIVE DEMO (50% · 4 minutes)
# ═══════════════════════════════════════════════════════════

> [!TIP]
> **Golden rules for the live demo:**
> - Say one sentence **before** each click: what will happen
> - Never say "as you can see" — say "top line", "second line"
> - After an answer appears, **pause one second** so judges can read
> - If something breaks: *"and this is why we built the fallback"* — and move on

---

### DEMO BEAT 1: Login (4:00 – 4:10 · 10 s)

**[Screen: `/login` — live clock ticking]** **[Click `[ DEMO ACCESS ]`]**

> *"A real running system, not slides. One click — we're in as an Inspector."*

---

### DEMO BEAT 2: The direct answer (4:10 – 5:00 · 50 s)

**[Screen: `/antar` · Expert mode ON · language EN]**
**[Type: `most crimes?`]**

> *"Two words. Watch it think — step by step."*

**[Point at the thinking steps, then "Thought for …s"]**

**Screen shows:**
> **[COMPUTED] Bengaluru City** has the most crime — **177,209** FIRs, 42% of the Karnataka total.
> • Direction: STABLE …
> Top 10 districts …

> *"Top line — Bengaluru City, one lakh seventy-seven thousand FIRs, forty-two percent of the state."*
> *"Second line — is it rising or falling. Then the proof."*
> *"And this tag says COMPUTED. It counted. It didn't guess."*

---

### DEMO BEAT 3: Kannada, by voice (5:00 – 5:40 · 40 s)

**[Switch language to ಕನ್ನಡ · tap mic · say: "ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಎಲ್ಲಿ?" · send]**

> *"Now the way a police station actually talks."*

**Screen shows:** **Bengaluru City** ನಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಪ್ರಕರಣಗಳು — **26,329** FIR, 54% — and it reads it out loud.

> *"Same engine. Same real count. Answered in Kannada — and spoken back. A constable can use this on a phone."*

**If the mic mishears:** type the same question.

---

### DEMO BEAT 4: Connect — Yellappa's network (5:40 – 6:30 · 50 s)

**[Language back to EN · Type: `what crimes is S0001 linked to`]**

> *"Remember Yellappa? Let's ask."*

**Screen shows:**
> **[VERIFIED] S0001** is linked to **8** cases …
> **Criminal network — S0001** · 6 known associates across 9 links

**[Click the network icon under the answer]**

> *"Eight cases. Two districts. Six people around him. One click — and you see the network. What took days now takes one question."*

---

### DEMO BEAT 5: Anticipate (6:30 – 7:05 · 35 s)

**[Type: `predict theft next month in Bengaluru City`]**

**Screen shows:** a next-month estimate with its range, and a **7-day risk outlook** (risk level + confidence).

> *"From pattern to foresight. An estimate with its range — and a seven-day risk level to plan patrols. An estimate, never a promise."*

**[Click "View on map" — Karnataka with every district]**

---

### DEMO BEAT 6: Proof — the sealed report (7:05 – 7:35 · 30 s)

**[Click the Export report icon under any answer]**

> *"Everything we just asked — now one report. Each question, how it was answered, which FIRs it came from, how long it took. Sealed with SHA-256. This is what lets an officer put an answer in a case file."*

---

### DEMO BEAT 7: Trust — Trace (7:35 – 7:50 · 15 s)

**[Navigate to `/trace`]**

> *"And every question from this demo is here — the template used, the rows returned, the timing. Nothing is hidden."*

---

### CLOSING — The Punchline (7:50 – 8:00 · 10 s)

> *"Antar **thinks** — it sends each question to the right specialist. It **connects** — it finds the links across districts. And it **anticipates** — it tells you where to look next."*
>
> *"Four lakh FIRs. Kannada and English. No made-up numbers. Proof in one click. Thank you."*

**[Hold silence. Let it land.]**

---

# ═══════════════════════════════════════════════════════════
# APPENDIX: Q&A PREP — Short answers
# ═══════════════════════════════════════════════════════════

### Q: "How do you prevent hallucination?"
> **A:** The AI never writes SQL — it picks one of 13 whitelisted templates with validated parameters. The numbers are counted from the rows returned, and if a place, name or ID isn't on record, Antar says so instead of guessing.

### Q: "What if the LLM is down?"
> **A:** Antar routes with its own deterministic router first, and a circuit breaker stops calling a failing model after one bad response. The same templates run and the answer is written from the data — the officer still gets an answer in one to five seconds.

### Q: "Is the Kannada voice real?"
> **A:** Yes. Kannada speech goes in through the browser's speech recognition, answers are written from Kannada templates, and read back with text-to-speech. Place names stay as written in the FIRs.

### Q: "Can it scale?"
> **A:** It's deployed on Zoho Catalyst AppSail, CPU-only. Answers are fast database counts with caching, not long AI generations, and each agent has its own timeout and circuit breaker.

### Q: "Privacy?"
> **A:** Personal details are redacted before any text reaches the AI, every question is logged with the officer's ID in a hash-chained audit log, and sensitive views like the network graph are locked by rank.

### Q: "How accurate is it?"
> **A:** A bilingual golden-question suite must route at least 90% correctly in English and Kannada, and 620 automated tests pass on the build. Every report lists the exact FIRs, so any answer can be checked by hand.

---

# ═══════════════════════════════════════════════════════════
# APPENDIX: PRE-DEMO CHECKLIST
# ═══════════════════════════════════════════════════════════

- [ ] Start backend on **port 8000**: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Start frontend: `cd antar-frontend && npm run dev` (it calls the backend on 8000)
- [ ] Open `http://127.0.0.1:8000/docs` to confirm the backend is up
- [ ] Ask every demo question once (warms the cache → faster on stage)
- [ ] Check the numbers in this script still match the screen (direction lines change with the date)
- [ ] Login with `[ DEMO ACCESS ]`, click **New Session**, confirm "Direct Chat mode active"
- [ ] Expert mode ON before Beat 2
- [ ] Allow microphone; test the Kannada question **in the room**
- [ ] Speakers on, volume up for the Kannada read-back
- [ ] Backup tabs open: S0001 network graph + one exported report
- [ ] Questions typed in a notepad to paste if voice fails
- [ ] Mobile hotspot ready
- [ ] `DEMO_MODE=true` in `.env` if LLM credentials are unavailable
- [ ] Record a 90-second backup video of the full demo

---

> [!CAUTION]
> **If anything breaks:** Don't panic. Say: *"And this is exactly why we built the fallback."* Move to the next beat. Never apologise.
