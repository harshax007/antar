"use client";
// Data protection and governance: how Antar handles personal data, written for an officer,
// a supervisor and an auditor. Every line here describes something the code does; the file
// it lives in is named beside it so it can be checked, not taken on trust.
import Link from "next/link";
import { useLang } from "@/components/Providers";
import "@/components/editorial-governance.css";

const ROLES = [
  ["Constable", "Case rows of their own posting; statewide counts."],
  ["Inspector", "Adds people, networks, dossiers and open-web checks, and may propose an action."],
  ["Analyst", "Case rows statewide; may propose an action."],
  ["Approver", "Decides proposed actions. Cannot decide their own."],
  ["Admin", "Accounts and the audit log."],
  ["Superintendent", "Reads everything an Admin can, and approves actions."],
];

const SECTIONS = [
  {
    key: "law", en: "The law it works under", kn: "ಅನ್ವಯಿಸುವ ಕಾನೂನು",
    items: [
      ["Digital Personal Data Protection Act, 2023",
       "Processing to prevent, detect, investigate or prosecute an offence is exempt from most of the Act (s.17(1)(c)). The duty to keep the data secure (s.8(5)) still applies. Antar is built to the stricter standard anyway: a stated purpose, the least data an answer needs, and a stated retention."],
      ["Constitution, Article 15",
       "Every question is screened before any data agent sees it. A request that targets people by caste, religion or community is refused, with the article cited, and the refusal is logged.",
       "app/agents/vigil_agent.py"],
      ["BNSS, 2023",
       "Requests for personal data beyond what a case needs are flagged against the order they would require. Pending investigations are shown against the s.187(3) 60- and 90-day marks.",
       "app/agents/vigil_agent.py · app/services/case_timeline.py"],
    ],
  },
  {
    key: "purpose", en: "Purpose and need to know", kn: "ಉದ್ದೇಶ ಮತ್ತು ಅಗತ್ಯ ಮಾಹಿತಿ",
    lede: "Antar exists to help police prevent and investigate crime. Who may see what is decided on the server from the signed-in account, by the route and again before each agent runs, never by the screen.",
    roles: true,
    items: [
      ["Your district first",
       "Below Analyst, an officer with a posting reads individual cases of that district only. Counts for other districts stay visible.",
       "app/services/zcql_repo.py · need_to_know"],
      ["A check per agent",
       "Each agent declares how sensitive its output is and the lowest role that may run it. A lower role is refused before the agent starts.",
       "AGENTS.md · app/core/policy.py"],
    ],
  },
  {
    key: "minimum", en: "The least data an answer needs", kn: "ಕನಿಷ್ಠ ಮಾಹಿತಿ",
    items: [
      ["Identity numbers masked", "Aadhaar and mobile numbers are cut to their last four digits in answers, traces and audit rows.", "app/core/guardrails.py · redact_pii"],
      ["Aggregates stay aggregates", "Social and demographic insight is counts only, with a note that it is never a basis to target a group. Agents declared aggregate-only cannot return a person, whatever their code tries.", "app/core/policy.py · aggregate_only"],
      ["No complainant names", "The field that can carry a complainant's name is never read by the map.", "app/api/map_api.py"],
      ["Stand-in names", "Where the record holds only an accused id, the name shown is made by the system and labelled as such.", "app/services/evidence_ledger.py"],
    ],
  },
  {
    key: "account", en: "Accountability", kn: "ಹೊಣೆಗಾರಿಕೆ",
    items: [
      ["A tamper-evident audit log", "Every request is written with who asked, their role and the policy decision. Each row carries the hash of the one before it, so a deleted or altered row breaks the chain. Rows are never deleted; an archive keeps the link to the chain it came from.", "app/services/audit_store.py"],
      ["A second person for real-world actions", "A patrol redeployment or a watchlist addition is only proposed. A supervising officer approves it, never the proposer, against the exact version they reviewed. Unapproved proposals expire (12 hours for patrols, 72 for watches).", "app/core/hitl.py"],
      ["Every answer shows its sources", "Answers cite the FIRs they rest on and the steps taken. Claims the rows do not support are removed before the answer is shown.", "app/agents/answer_writer.py · /trace"],
      ["What runs is what was reviewed", "Agent code and prompts are locked by hash. In production a mismatch stops the system from starting.", "agents.lock.json"],
    ],
  },
  {
    key: "keep", en: "How long data is kept", kn: "ಮಾಹಿತಿ ಎಷ್ಟು ಕಾಲ ಉಳಿಯುತ್ತದೆ",
    table: [
      ["Sign-in", "8 hours, one shift. Ends at sign-out, or when an Admin ends an officer's sessions."],
      ["Conversation memory", "30 days after its last use, then deleted when the system starts."],
      ["Saved conversations", "Encrypted on disk (AES-128 with an integrity check) and readable only by the officer who saved them, or an Admin. There is no automatic expiry yet."],
      ["Audit log", "Kept. Never deleted; archived with its chain intact."],
    ],
  },
  {
    key: "secure", en: "Security safeguards", kn: "ಭದ್ರತಾ ಕ್ರಮಗಳು",
    items: [
      ["Signed sign-in", "Passwords are stored only as salted scrypt hashes. Five wrong attempts lock an account for five minutes, and sign-in is rate-limited. Every request carries a signed, expiring token.", "app/core/accounts.py · auth_middleware.py"],
      ["Refuses to run unsafely", "In production the system will not start without its signing secret, or with agent code that differs from what was reviewed.", "app/core/security.py"],
      ["What leaves the building", "Every outbound call is checked against one list and counted, logging the host only, never what was sent. One setting stops all outbound calls; each feature then falls back to the record.", "app/core/egress.py"],
      ["The open web is never the record", "Open-web results are labelled unverified, never merged into case data, and refused without a named subject.", "app/agents/graph.py · osint"],
    ],
  },
  {
    key: "not", en: "What Antar does not do", kn: "ಅಂತರ್ ಮಾಡದಿರುವುದು",
    items: [
      ["Forecast people", "Forecasts are about places and periods. A risk score on a named accused orders the record for an investigating officer, shows each factor that made it and passes a bias screen."],
      ["Act on its own", "No real-world action happens without a named officer's approval."],
      ["Replace the investigating officer", "A link, a lead or a similar case is a reason to look, not a finding. Inferred claims are marked as inferred and checked against base rates before they can be confirmed."],
    ],
  },
];

export default function GovernancePage() {
  const { lang } = useLang();
  const kn = lang === "kn";
  return (
    <main className="gv-page">
      <div className="gv-wrap">
        <header className="gv-head">
          <span className="gv-eyebrow">{kn ? "ಮಾಹಿತಿ ಸಂರಕ್ಷಣೆ" : "Data protection"}</span>
          <h1>{kn ? "ಅಂತರ್ ಮಾಹಿತಿಯನ್ನು ಹೇಗೆ ನಿರ್ವಹಿಸುತ್ತದೆ" : "How Antar handles data"}</h1>
          <p>Antar reads police records about real people. This page says what it does with them: the law it follows, who can see what, what is kept and for how long, and how every step can be checked afterwards.</p>
          <p className="gv-who">For officers who use it, supervisors who answer for it, and auditors who check it. Each claim names the part of the system that makes it true, so it can be verified rather than trusted.</p>
          <div className="gv-cta">
            <Link className="ui-btn ui-btn--primary" href="/trace">See the audit trail</Link>
            <span>Every request, who made it, and the decision taken</span>
          </div>
          {kn && <p className="gv-kn-note">ಈ ಪುಟದ ವಿವರಗಳು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿವೆ.</p>}
        </header>

        <nav className="gv-toc" aria-label={kn ? "ವಿಭಾಗಗಳು" : "Sections"}>
          {SECTIONS.map((s, i) => <a key={s.key} href={`#${s.key}`}><span>{String(i + 1).padStart(2, "0")}</span>{kn ? s.kn : s.en}</a>)}
        </nav>

        {SECTIONS.map((s, i) => (
          <section key={s.key} id={s.key} className="gv-sec">
            <h2><span>{String(i + 1).padStart(2, "0")}</span>{kn ? s.kn : s.en}</h2>
            {s.lede && <p className="gv-lede">{s.lede}</p>}
            {s.roles && (
              <dl className="gv-roles">
                {ROLES.map(([r, what]) => <div key={r}><dt>{r}</dt><dd>{what}</dd></div>)}
              </dl>
            )}
            {s.items && (
              <ul className="gv-items">
                {s.items.map(([t, body, where]) => (
                  <li key={t}>
                    <b>{t}</b>
                    <p>{body}</p>
                    {where && <code>{where}</code>}
                  </li>
                ))}
              </ul>
            )}
            {s.table && (
              <dl className="gv-roles gv-keep">
                {s.table.map(([what, how]) => <div key={what}><dt>{what}</dt><dd>{how}</dd></div>)}
              </dl>
            )}
          </section>
        ))}

        <p className="gv-foot">A person named in the record cannot use Antar to see or correct it; that runs through the police's own processes. Antar's part is that every figure traces back to the rows it came from.</p>
      </div>
    </main>
  );
}
