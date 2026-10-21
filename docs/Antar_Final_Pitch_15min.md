# 🎯 ANTAR — Final Demo Pitch Material · 15-MINUTE VERSION

> **Team Vimaraksha · Datathon 2026 · Final Day In-Person Demo**
> Slot: **15 minutes** · Speaker talks, Driver types · Everything below matches the current build

---

## PITCH STRUCTURE OVERVIEW

| Section | Weight | Time (15 min) | Clock | Goal |
|---------|--------|---------------|-------|------|
| **WHY** | 20% | 3 min | 0:00 – 3:00 | How we *read* the problem — our insight, not the problem statement |
| **HOW** | 30% | 4 min 30 s | 3:00 – 7:30 | Our approach, architecture, and *why it wins* |
| **WHAT** | 50% | 7 min 30 s | 7:30 – 15:00 | Live demo — chat, network, brain, map, predict, proof |

> [!NOTE]
> **Facts updated from the draft** — say these, not the old ones:
> 10,00,000 FIRs · **41 districts · 1,155 police stations · 2,365 suspects · 2,748 victims** · 113 crime types · 2016–2026 · **26** whitelisted question templates · typical answer **2.8 seconds** (median) · 1,395 automated tests · "Yellappa" is the alias of **Raju K. (S0001)**: 6 priors, 8 linked cases, 2 districts, 6 associates.
> Removed because they are not in the build: Section 65B / BSA compliance, DPDP toggles, "98.4% clean rate", map time slider.

---

# ═══════════════════════════════════════════════════════════
# SECTION 1: START WITH WHY (20% · 3 minutes)
# ═══════════════════════════════════════════════════════════

> [!IMPORTANT]
> **Do NOT say**: "Crime is a big problem and police need better tools."
> **DO say**: "We sat with the data and found three gaps no dashboard fixes."

### 🎤 SPEAKER SCRIPT — WHY

**[0:00 — Hook. Say the number. Then silence.]**

> *"Four lakh twenty-five thousand."*
>
> *"That's how many FIRs are in the Karnataka police data we were given. Forty-one districts. Over a thousand police stations. More than a hundred types of crime, across ten years."*

**[PAUSE]**

**[0:25 — The real example]**

> *"Let me tell you about one suspect. Raju K. On the street, they call him 'Yellappa'."*
>
> *"Six prior offences. Linked to eight cases — some in Rajajinagar in Bengaluru, some in Bagalkot, three hundred kilometres away. Six people connected to him. And one of those Bagalkot FIRs shares his phone."*
>
> *"Every one of those facts is already in the data. But to put them together, an officer needs days, phone calls between two districts — and luck. Because the answer is **scattered across tables, districts and time**."*

**[1:15 — What we saw: three gaps]**

> *"When we looked closer, we saw three gaps."*
>
> *"**The language gap.** Officers think in Kannada, and in questions. The data only understands database queries."*
>
> *"**The trust gap.** A number that can't be traced back to an FIR can't go in a case file. And an AI that makes up a number is dangerous."*
>
> *"**The time gap.** By the time an analyst builds a report, the pattern has already moved."*

**[2:15 — Our reframe]**

> *"So we stopped thinking 'dashboard'. This isn't a chart problem. It's an **intelligence assembly problem**."*
>
> *"The officer's real question is: **what should I know right now — and can I prove it?** In my own language. In seconds."*
>
> *"That reframe shaped every decision we made. We built **Antar**. It thinks. It connects. It anticipates."*

**[3:00 — Hand-off]** *"Let me show you how it works."*

### Key Talking Points (WHY)
- **10,00,000 FIRs**, 41 districts, 1,155 stations, 113 crime types — real scale
- Real example: **Raju K. alias Yellappa (S0001)** — 8 cases, 2 districts, shared phone
- **Three gaps: language, trust, time**
- Reframe: **"assemble intelligence and prove it"**, not "show charts"
- Tagline: **"Think. Connect. Anticipate."**

---

# ═══════════════════════════════════════════════════════════
# SECTION 2: HOW (30% · 4 min 30 s)
# ═══════════════════════════════════════════════════════════

### 🎤 SPEAKER SCRIPT — HOW

**[3:00 — A team of specialists]**

> *"You don't solve this with one big AI. You solve it the way a real investigation works — with a **team of specialists**."*

**[3:15 — What happens when you ask a question]**

> *"When an officer asks something — in English or Kannada, typed or spoken — five things happen, in one to five seconds:"*
>
> 1. *"A **Supervisor** works out what kind of question it is — a count, a trend, a suspect, a network, a forecast."*
> 2. *"The **records agent** picks one of thirteen safe question templates and runs it on the FIRs. The AI never writes database code."*
> 3. *"**Specialist agents** join in — the network agent finds links with PageRank and link prediction, the profile agent scores risk, the forecast agent looks for unusual spikes."*
> 4. *"A **Synthesizer** writes one clear answer — the answer first, which way it's moving, then the proof."*
> 5. *"And that answer is **sealed** into a tamper-proof audit log."*

**[4:15 — Four things that make it different]**

> **"One — it doesn't make up numbers."**
> *"The numbers are counted from real FIRs and tagged: COMPUTED if we counted it, VERIFIED if it's a record. If a name or a place isn't in the data, Antar says 'not on record'. It never invents."*

> **"Two — it's built for Kannada, not translated into it."**
> *"Ask in Kannada, by voice or text. The answer comes back in Kannada, with Kannada crime names — and it reads it out loud."*

> **"Three — it remembers. We call it the Second Brain."**
> *"When the system finds a link between cases, that finding is stored as memory using BGE embeddings. The next officer, on a different day, gets that finding back. Antar gets smarter with every investigation."*

> **"Four — it's ready for a case file."**
> *"Every answer is hash-chained into the audit log. One click turns a session into a sealed PDF — every question, its method, the FIRs behind it, the time it took, and a SHA-256 seal."*

**[6:15 — Transparent, not a black box]**

> *"The risk score is a simple, visible formula — recency, frequency, severity and network centrality — and the officer sees every factor. Forecasts come with a range, and they separate festival seasons like Dasara from real unusual spikes."*

**[6:50 — It ships]**

> *"And it runs on CPU only, deployed on Zoho Catalyst. Each agent has its own timeout and circuit breaker. If the cloud AI is slow or down, Antar switches to its verified path — and keeps answering."*

**[7:30 — Hand-off]** *"Enough talking. Let's ask it."*

### Key Talking Points (HOW)
- **Supervisor → specialist agents → Synthesizer** (LangGraph)
- **13 whitelisted templates** — the AI selects, never writes SQL
- **COMPUTED / VERIFIED tags**; "not on record" instead of guessing
- **Kannada-native** answers, voice in and out
- **Second Brain** — BGE-embedded institutional memory
- **Hash-chained audit** + SHA-256 sealed report
- **Transparent risk score** (4 visible factors) · forecasts with ranges
- **CPU-only on Catalyst**, per-agent circuit breakers, 1–5 s answers

---

# ═══════════════════════════════════════════════════════════
# SECTION 3: WHAT — LIVE DEMO (50% · 7 min 30 s)
# ═══════════════════════════════════════════════════════════

> [!TIP]
> **Golden rules for the live demo:**
> - Say one sentence **before** each click: what will happen
> - Never say "as you can see" — say "top line", "this badge"
> - Pause one second after each answer appears
> - If something breaks: *"and this is why we built the fallback"* — move on

---

### DEMO BEAT 1: Login (7:30 – 7:45 · 15 s)

**[Screen: `/login` — live clock ticking]** **[Click `[ DEMO ACCESS ]`]**

> *"This is a real running system — look, the clock is live. One click, and we're in as an Inspector."*

---

### DEMO BEAT 2: The direct answer (7:45 – 8:35 · 50 s)

**[Screen: `/antar` · Expert mode ON · language EN · Type: `most crimes?`]**

> *"I'll ask the simplest question there is. Watch it think."*

**[Point at the thinking steps appearing one by one, then "Thought for …s"]**

**Screen shows:**
> **[COMPUTED] Bengaluru City** has the most crime — **177,209** FIRs, 42% of the Karnataka total.
> • Direction: STABLE …
> Top 10 districts …

> *"Top line — the answer. Bengaluru City, one lakh seventy-seven thousand FIRs, forty-two percent."*
> *"Second line — is it rising or falling."*
> *"Then the evidence. And this COMPUTED tag — it counted. It didn't guess."*

---

### DEMO BEAT 3: Kannada, by voice (8:35 – 9:20 · 45 s)

**[Switch to ಕನ್ನಡ · tap mic · say: "ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಎಲ್ಲಿ?" · send]**

> *"Now let's talk the way a police station talks."*

**Screen shows:** **Bengaluru City** ನಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಪ್ರಕರಣಗಳು — **26,329** FIR, 54% — read out loud.

> *"Twenty-six thousand thefts. More than half in Bengaluru City. Answered in Kannada — and spoken back. A constable in a rural station can use this on a phone."*

---

### DEMO BEAT 4: "Why did you say that?" (9:20 – 9:40 · 20 s)

**[Type: `why?`]**

> *"And if the officer asks why —"*

**Screen shows:** a numbered list of the steps Antar took.

> *"— it shows its reasoning, step by step. Nothing hidden."*

---

### DEMO BEAT 5: Connect — Yellappa's network (9:40 – 10:40 · 60 s)

**[Language back to EN · Type: `what crimes is S0001 linked to`]**

> *"Remember Yellappa? Let's ask about him."*

**Screen shows:**
> **[VERIFIED] S0001** is linked to **8** cases …
> **Criminal network — S0001** · 6 known associates across 9 links

**[Click the network icon → graph opens]**

> *"Eight cases. Two districts. Six people around him. The node size is PageRank — who matters most in this network. What took days now takes one question."*

---

### DEMO BEAT 6: The Second Brain (10:40 – 11:25 · 45 s)

**[Navigate to `/antarBrain` — 3D constellation loads · rotate slowly]**

> *"This is the Second Brain. Every point is a crime event. The lines are links the system found between cases."*

**[Click a large hub node — camera flies in, drawer opens]**

> *"I click a hub — and it tells me which cases are linked, and why. Nobody asked for this link. **The system found it.**"*

---

### DEMO BEAT 7: The Map (11:25 – 12:25 · 60 s)

**[Navigate to `/map` — Karnataka outline with all districts]**

> *"Now, where. Every district of Karnataka, shaded by how much crime it has."*

**[Point at the hotspot markers]**

> *"These hotspots aren't a guess. They come from the Getis-Ord statistic — a standard method in criminology for real, significant clusters."*

**[Click a district — drawer opens]**

> *"Click any district — the top crime types, the stations, and where to focus patrols."*

---

### DEMO BEAT 8: Predict (12:25 – 13:25 · 60 s)

**[Navigate to `/predict`]**

> *"And finally — when."*

**[Point at a forecast row — read the range on screen]**

> *"Each forecast is a range, not a single number — with its coverage. And it knows the difference between a festival season like Dasara and a real, unusual spike."*

**[Point at the reasoning graph]**

> *"And this shows exactly which signals fed the prediction."*

---

### DEMO BEAT 9: Honest when it doesn't know (13:25 – 13:45 · 20 s)

**[Back to `/antar` · Type: `theft in Atlantis`]**

**Screen shows:** • Note: "Atlantis" isn't a district or police station on record — showing all of Karnataka instead.

> *"A normal chatbot might invent Atlantis. Antar tells you it isn't on record."*

---

### DEMO BEAT 10: Proof — sealed report (13:45 – 14:25 · 40 s)

**[Click the Export report icon]**

> *"Everything we asked today — now one report. Each question, the method, the FIRs it came from, how long it took. Sealed with SHA-256. An officer can put this in a case file."*

---

### DEMO BEAT 11: Trust — Trace (14:25 – 14:45 · 20 s)

**[Navigate to `/trace`]**

> *"And every question from this demo is inspectable here — the template, the rows, the timing, per question."*

---

### CLOSING — The Punchline (14:45 – 15:00 · 15 s)

> *"Antar **thinks** — sending each question to the right specialist. It **connects** — finding links across districts nobody asked for. And it **anticipates** — showing where and when to look next."*
>
> *"Four lakh FIRs. Kannada and English. No made-up numbers. Proof in one click. Thank you."*

**[Hold silence. Let it land.]**

---

# ═══════════════════════════════════════════════════════════
# APPENDIX: Q&A PREP — Likely Judge Questions
# ═══════════════════════════════════════════════════════════

### Q: "How do you prevent hallucination?"
> **A:** The AI never writes SQL — it picks one of 13 whitelisted templates with validated parameters. The numbers are counted from the returned rows and tagged COMPUTED or VERIFIED, and if a name, place or ID isn't on record, Antar says so instead of guessing.

### Q: "What happens when the LLM is unavailable?"
> **A:** Routing is deterministic first, and a circuit breaker stops calling a failing model after one bad response. The same templates run and the answer is written straight from the data — the officer still gets an answer in one to five seconds.

### Q: "How does the risk score work? Isn't it biased?"
> **A:** It's a visible four-factor formula — recency, frequency, severity and network centrality — and the officer sees every factor bar. Profiles also run a bias check, and social insights are aggregate-only with a warning not to target any group.

### Q: "Is the Kannada voice real?"
> **A:** Yes. Kannada speech comes in through speech recognition, answers are written from Kannada templates with Kannada crime and status names, and read back with text-to-speech. The backend also has a Bhashini integration for translation.

### Q: "Can this scale to production?"
> **A:** It's deployed on Zoho Catalyst AppSail, CPU-only. Answers are indexed database counts with caching, and every agent has its own timeout, retries and circuit breaker.

### Q: "What about privacy?"
> **A:** Personal details are redacted before any text reaches the AI. Every question is logged against the officer's ID in a hash-chained audit log, and sensitive views like the network graph are locked by rank — a constable can't open them.

### Q: "What's the Second Brain? How is it different from RAG?"
> **A:** Normal RAG looks up documents to answer one question. The Second Brain stores what the system *discovers* — like a link between two cases — as BGE embeddings, so a different officer's later question can retrieve it. It's a shared detective notebook that grows.

### Q: "How accurate is it?"
> **A:** A bilingual golden-question suite must route at least 90% correctly in English and Kannada before a build ships, and 620 automated tests pass. Every report lists the method and the exact FIRs, so any answer can be checked by hand.

---

# ═══════════════════════════════════════════════════════════
# APPENDIX: PRE-DEMO CHECKLIST
# ═══════════════════════════════════════════════════════════

- [ ] Start backend on **port 8000**: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Start frontend: `cd antar-frontend && npm run dev`
- [ ] Open `http://127.0.0.1:8000/docs` to confirm the backend is up
- [ ] Ask every demo question once (warms the cache → faster on stage)
- [ ] Check this script's numbers against the screen (direction lines change with the date)
- [ ] Open `/antarBrain`, `/map`, `/predict` once so they're loaded
- [ ] Login with `[ DEMO ACCESS ]`, **New Session**, confirm "Direct Chat mode active"
- [ ] Expert mode ON before Beat 2
- [ ] Allow microphone; test the Kannada question **in the room**
- [ ] Speakers on, volume up for the Kannada read-back
- [ ] Backup tabs: S0001 network graph + one exported report
- [ ] Questions in a notepad to paste if voice fails
- [ ] Clear browser cache if the 3D Brain is slow
- [ ] Mobile hotspot ready
- [ ] `DEMO_MODE=true` in `.env` if LLM credentials are unavailable
- [ ] Record a 2-minute backup video of the full demo

---

> [!CAUTION]
> **If anything breaks:** Don't panic. Say: *"And this is exactly why we built the fallback — the system keeps working."* Move to the next beat. Never apologise.
