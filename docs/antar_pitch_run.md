# Antar — Pitch Run (easy-to-say version)

**Slot:** 7 minutes · **Split:** Why 20% (1:25) · How 30% (2:05) · What 50% (3:30)
**Two people:** the **Speaker** talks, the **Driver** types. If you're alone, stop talking while you type.

> **Our one line (say it at the start and the end):**
> **"Ask in Kannada. Get the answer in seconds. Trust every number."**

---

## How to read this script

- **Bold lines** are what you say. Say them slowly, like talking to a friend.
- *Italic lines* are what you do.
- Short sentences on purpose. Breathe at every full stop.
- Numbers are written the way you say them out loud.

---

## 1. WHY — how we saw the problem (0:00 – 1:25)

**Goal:** judges agree the hard part is *trust*, not *chat*.

### The story (0:00 – 0:25)
*Home screen on the projector. Nothing typed. Stand still.*

**"It's 11:40 at night. Rajajinagar police station."**
**"A chain-snatching complaint comes in. The third one this week."**
**"The officer has four lakh twenty-five thousand FIRs in the system."**
**"But she can't ask them a single question. Not in her language. Not at night. Not without an analyst."**

### What we saw (0:25 – 1:05)
**"When we read this challenge, we didn't think: build a chatbot."**
**"We saw three gaps."**

**"One — language. Officers think in Kannada. The data only understands database queries."**
**"Two — trust. If a number can't be traced back to an FIR, it can't go in a case file. And an AI that makes up numbers is dangerous."**
**"Three — time. By the time someone builds a report, the pattern has already moved."**

### Our goal (1:05 – 1:25)
**"So our goal was simple."**
**"An officer asks in her own language. She gets the answer in seconds. And she can trust every number in it."**
**"That's Antar."**

*Hand-off line:* **"Let me show you how it works."** *(Driver goes to the keyboard.)*

---

## 2. HOW — our approach (1:25 – 3:30)

**Goal:** judges remember one idea — **Antar counts the answer, it doesn't guess it.**

### The big idea (1:25 – 1:45)
**"Antar is built on one rule."**
**"The AI understands your question. But it never makes up the numbers."**
**"The numbers are counted from the real FIR records."**

### How it works — 5 simple steps (1:45 – 2:15)
**"Here's what happens when you ask something."**

1. **"You ask — by typing or speaking, in English or Kannada."**
2. **"Antar understands what you want — which crime, which place, which time."**
3. **"It picks one of 13 checked, safe question types and runs it on the FIR data."**
4. **"Helper agents add more — links between suspects, patterns, forecasts, the map."**
5. **"You get the answer, and it's saved in a secure log."**

**"Every answer has a tag. COMPUTED means we counted it. VERIFIED means we looked up the record."**

### Four promises (2:15 – 3:30)
**"This gives us four promises."**

**"One — the answer comes first. Like a good officer briefing their boss: the answer, which way it's going, then the proof."** *(2:15)*

**"Two — Kannada is built in. Ask in Kannada, by voice or text, and it answers in Kannada. It even reads the answer out loud."** *(2:35)*

**"Three — it's ready for court. Every answer is locked in a tamper-proof log. One click turns the whole session into a sealed PDF report."** *(2:55)*

**"Four — it's fast and it doesn't break. You see it thinking in a tenth of a second. Answers come in one to five seconds. And if the cloud AI goes down, Antar still answers."** *(3:15)*

*Hand-off line:* **"Enough talking. Let's ask it."**

### If a judge asks "why not just ChatGPT?" (keep for Q&A)
| What an officer needs | ChatGPT-style chatbot | Dashboard | Antar |
|---|---|---|---|
| Ask in Kannada | Partly | No | **Yes** |
| Every number from real FIRs | No — it guesses | Only fixed charts | **Yes** |
| New question, no analyst needed | Yes | No | **Yes** |
| Says "not on record" | Rarely | — | **Yes** |
| Sealed report for a case file | No | No | **Yes** |
| Works if the AI is down | No | Yes | **Yes** |

---

## 3. WHAT — live demo (3:30 – 7:00)

**Goal:** show every promise working, with one real number each.
**Before starting:** Expert mode ON · Language on EN · New session.

---

### Demo 1 — The direct answer (3:30 – 4:10)
*Type:* `most crimes?`

**On screen:** thinking steps appear one by one, then "Thought for 3.6s", then:
> **Bengaluru City** has the most crime — **177,209** FIRs, 42% of the Karnataka total.
> • Direction: STABLE
> Top 10 districts: …

**Say:**
**"Just two words."**
**"You can see it thinking, step by step."**
**"And here's the answer. Bengaluru City. One lakh seventy-seven thousand FIRs. Forty-two percent of the state."**
**"Second line — is it going up or down. Right now, stable."**
**"And see this tag — COMPUTED. It counted this. It didn't guess."**

*If it's slow:* **"It's counting four lakh records right now."** *(Nothing after 10 seconds → switch to the backup tab.)*

---

### Demo 2 — Kannada, by voice (4:10 – 4:45)
*Switch language to ಕನ್ನಡ. Tap the mic. Say:* **ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಎಲ್ಲಿ?** *(Where is theft highest?) Then send.*

**On screen:**
> **Bengaluru City** ನಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ — **26,329** FIR, 54%
> …and it reads the answer out loud.

**Say:**
**"Now let's talk the way a police station talks."**
*(Driver speaks the question.)*
**"Same system. Same real count. Twenty-six thousand thefts — more than half in Bengaluru City."**
**"Answered in Kannada. And spoken back."**

*If the mic mishears:* type the same question. **"Voice works best in a quiet station."**

---

### Demo 3 — Links between suspects (4:45 – 5:25)
*Switch language back to EN. Type:* `what crimes is S0001 linked to`

**On screen:**
> **S0001** is linked to **8** cases …
> **Criminal network — S0001** · 6 known associates across 9 links

*Click the network icon under the answer.*

**Say:**
**"Now relationships."**
**"One suspect. Eight cases. Six people connected to him."**
**"One click — and you see the whole network. Not a spreadsheet."**

*If it's slow:* open the Network tab.

---

### Demo 4 — What happens next (5:25 – 6:00)
*Type:* `predict theft next month in Bengaluru City`

**On screen:**
> • Next month (estimate): about **34** cases (range 32–36)
> **7-day risk:** Elevated (75% confidence)

*Click "View on map".*

**Say:**
**"Now the future."**
**"About thirty-four thefts expected next month. And we show the range."**
**"Plus a seven-day risk level, so you can plan patrols."**
**"It's an estimate, not a promise — and we say that clearly."**

*If it's slow:* open the Predict tab.

---

### Demo 5 — Honest when it doesn't know (6:00 – 6:20) — *cut this first if you're late*
*Type:* `theft in Atlantis`

**On screen:**
> • Note: "Atlantis" isn't a district or police station on record — showing all of Karnataka instead.

**Say:**
**"A normal chatbot might make something up here."**
**"Antar just says: this place isn't in our records. And tells you what it's showing instead."**

---

### Demo 6 — Ready for court (6:20 – 6:50)
*Click the Export report icon under any answer.*

**On screen:** every question, how it was answered, which FIRs were used, how long it took, and a security seal at the bottom.

**Say:**
**"Everything we just asked is now one report."**
**"Each question. How it was answered. Which FIRs it came from. How long it took."**
**"And it's sealed, so nobody can change it later."**
**"That's what lets an officer put an answer in a case file."**

*If it's slow:* switch to the backup report tab.

---

### Close (6:50 – 7:00)
**"Ask in Kannada. Get the answer in seconds. Trust every number."**
**"That's Antar. Thank you."**

*Stop talking. Smile. Wait for questions.*

---

## Extra demos (use one instead of Demo 3 or 4 for policy-minded judges)
All four are suggestion buttons on the home screen.

| Question | What it shows | One line to say |
|---|---|---|
| `Fastest-growing crime groups 2021 to 2022?` | 2022: 1,95,170 FIRs (official total), up 11%. Cyber crime share 3.5% → 4.8% | **"Cyber crime's share grew by more than a third in one year."** |
| `IPC/BNS vs SLL split for 2022?` | 78% IPC/BNS, 22% special & local laws | **"More than one in five FIRs is a special or local law."** |
| `Crimes against women 2022 + top districts?` | Bengaluru City first, 21% of the state's cases | **"A question a senior officer really asks — answered with a ranked list."** |

Years: the demo asks about 2022 and reads shares and rankings, not raw counts. 2016-2022 rows are a partial extract (about a third of each year), and 2023-24 holds 100,000 duplicated rows (see `PROGRESS.md`, open risks). A yearly total quoted on screen is the official annual figure.
| `how many murders in Bengaluru City?` | 531 murder cases | **"Ask 'how many', and the number comes first."** |

---

## 3-minute version

| Time | Part | What to do |
|---|---|---|
| 0:00 – 0:35 | Why | The 11:40 pm story in two lines + "ask in her language, answer in seconds, trust every number." |
| 0:35 – 1:30 | How | One sentence each: counts not guesses · answer first · Kannada built in · sealed report. |
| 1:30 – 2:50 | What | Demo 1 (`most crimes?`), Demo 2 (Kannada voice), Demo 6 (report). |
| 2:50 – 3:00 | Close | The one line. Thank you. |

**5-minute slot:** skip Demo 5 and keep How to one sentence per promise.
**10-minute slot:** add two extra demos. Don't make the speeches longer.

---

## Numbers to remember

| Say this | Meaning |
|---|---|
| **"Four lakh twenty-five thousand FIRs"** | 425,009 records Antar answers from |
| **"Every district in Karnataka"** | 57 district/zone units |
| **"Over a hundred crime types"** | 117 types |
| **"About ten years of records"** | 2016 – 2026 |
| **"13 safe question types"** | the AI can only use checked queries |
| **"15 specialist agents"** | as shown on the home screen |
| **"Two languages, typed or spoken"** | English + Kannada, text + voice |
| **"Thinking in a tenth of a second"** | first step shows in ~0.1 s |
| **"Answers in one to five seconds"** | typical time |
| **"620 automated tests"** | all passing |
| **"Sealed report"** | SHA-256 seal on every export |

---

## Judges' questions — short answers

Answer in two sentences. Then offer: **"I can show you in ten seconds."**

**Q: How do you stop the AI from making up numbers?**
**"The AI never writes numbers. It picks a safe question type, and the numbers are counted from real FIRs. If something isn't in the records, it says so."**

**Q: What if the AI or the cloud goes down?**
**"Antar has a backup path that doesn't need the cloud AI. It still answers in one to five seconds — we've run this whole demo with the AI switched off."**

**Q: How do you know it's accurate?**
**"We test it with a fixed set of English and Kannada questions — it must get at least 90% right before we release. Plus 620 automated tests. And every report shows the exact FIRs, so anyone can check."**

**Q: Why not just use ChatGPT or Gemini?**
**"Police data can't leave the state's systems. ChatGPT guesses numbers — Antar counts them. And ChatGPT gives you no sealed record."**

**Q: What about privacy?**
**"Personal details are removed before anything reaches the AI. Every question is logged with the officer's ID. And sensitive screens, like the network graph, are locked by rank."**

**Q: Can it handle more data?**
**"Yes. Every answer is a fast database count, not a long AI response, and repeat questions are cached. The same design runs on our cloud database on Catalyst."**

**Q: Is the Kannada real or just Google Translate?**
**"It's real. Kannada questions are understood directly, and answers are written in Kannada, with Kannada crime names. Only place names stay as written in the FIRs."**

**Q: How reliable are the predictions?**
**"We show an estimate with a range, based on the last three full months. It's for planning patrols — not proof."**

**Q: Could it be used to target communities?**
**"No. Suspect profiles have a bias check, and social insights only show overall trends, with a clear warning not to target any group."**

**Q: What's the next step?**
**"A pilot in one district for three months. Officers rate every answer, and their most common questions tell us what to build next."**

### Q&A tips
- Repeat the question in a few words before answering.
- Technical questions → Driver. Impact / adoption questions → Speaker.
- If you don't know: **"We haven't measured that yet — here's how we would."** Never guess a number.

---

## On stage — simple rules

1. After an answer appears, **pause for one second.** Let the judges read.
2. Point with words — **"top line", "second line"** — don't wave the mouse around.
3. If something is slow, **say what it's doing.** Never say sorry.
4. **No code on screen.**
5. **Look at the judges,** not the screen. The Driver watches the screen.
6. **Practise the hand-offs** ("Let me show you how", "Let's ask it") — that's where time gets lost.

**Good words:** officer, counted, checked, real FIRs, in seconds, case file, sealed
**Avoid:** chatbot, hopefully, just, basically, AI magic, 100% accurate

---

## Checklist

**Night before**
- [ ] Restart the backend.
- [ ] Ask all six demo questions once (makes them faster on stage).
- [ ] Check the numbers in this script still match the answers.
- [ ] Record a 90-second backup video of the demo.
- [ ] Run the full pitch twice with a timer.
- [ ] Charge laptop, pack HDMI / USB-C adapter.

**One hour before**
- [ ] Chrome full screen, zoom 125%, notifications off.
- [ ] Log in with Demo Access, click New Session.
- [ ] Check it says "Direct Chat mode active" (Docs mode off).
- [ ] Allow the microphone, test the Kannada question in the room.
- [ ] Laptop sound to room speakers, volume up.
- [ ] Open backup tabs: S0001 network graph + a sample report.
- [ ] Phone hotspot ready.

**On stage**
- [ ] Expert mode ON before Demo 1.
- [ ] Timer where only the Speaker can see it.
- [ ] Language back to EN after Demo 2.
- [ ] Say the closing line — then stop.

---

**Heads-up:** The Direction lines and the forecast change with the date. The night before, re-run the demo questions and update any number that moved. The home screen says 15 agents while the code has 19 modules — pick one number and use it everywhere.
