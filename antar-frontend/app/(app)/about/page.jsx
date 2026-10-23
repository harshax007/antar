"use client";

import React from "react";
import { useLang } from "@/components/Providers";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export default function AboutPage() {
  const { lang } = useLang();
  const kn = lang === "kn";

  return (
    <div className="ab-page">
      <main className="ab-main">

        {/* Top Bar: Title + Meaning side by side */}
        <header className="ab-top">
          <div className="ab-top-left">
            <div className="ab-kicker">
              {kn ? "ತಂಡದ ಪರಿಚಯ" : "ABOUT US"}
            </div>
            <h1 className="ab-title">
              {kn ? "ಟೀಮ್ ವಿಮರಕ್ಷ" : "Team Vimaraksha"}
            </h1>
          </div>

          <div className="ab-meaning">
            <p className="ab-meaning-text">
              {kn ? (
                <>
                  <span className="ab-meaning-word">ಮುನ್ಸೂಚಕ ಭದ್ರತೆ</span>
                  <b>ವಿಮರಕ್ಷ</b>ದಲ್ಲಿ, ದಾಖಲೆಗಳಲ್ಲಿನ ಎಚ್ಚರಿಕೆಯ ಸೂಚನೆಗಳನ್ನು ಮೊದಲೇ ಗುರುತಿಸಿ, ಅಪರಾಧ ಸಂಭವಿಸುವ ಮುನ್ನವೇ ಸುರಕ್ಷತಾ ಕ್ರಮಗಳನ್ನು ಜಾರಿಗೆ ತರುವುದರ ಮೇಲೆ ನಾವು ಗಮನ ಹರಿಸುತ್ತೇವೆ.
                </>
              ) : (
                <>
                  <span className="ab-meaning-word">Predictive Security</span>
                  At <strong>Vimaraksha</strong>, we focus on putting secure measures in place before a crime happens, by spotting the warning signs early in the records.
                </>
              )}
            </p>
          </div>
        </header>

        {/* Middle Grid: How the Idea Started + Our Vision */}
        <div className="ab-mid-grid">
          <section className="ab-card">
            <div className="ab-sec-label">
              {kn ? "ಆಲೋಚನೆ ಪ್ರಾರಂಭವಾಗಿದ್ದು ಹೇಗೆ" : "HOW THE IDEA STARTED"}
            </div>
            <blockquote className="ab-origin-quote">
              {kn
                ? "“KSP ಬಳಿ ಬೃಹತ್ ಪ್ರಮಾಣದ FIR ದತ್ತಾಂಶವಿದೆ, ಆದರೆ ಅದರ ಮೇಲೆ ಯೋಚಿಸುವ ಬುದ್ಧಿವಂತ ಪದರ ಇಲ್ಲ, ಮತ್ತು ಆ ದತ್ತಾಂಶವನ್ನು ಸುರಕ್ಷಿತವಾಗಿ ಹೊರತೆಗೆಯುವುದು ಸುಲಭವಲ್ಲ.”"
                : "“KSP has a large amount of FIR data, but no intelligent layer that can think across it, and it is not easy to retrieve that data securely.”"}
            </blockquote>
            <p className="ab-card-text">
              {kn
                ? "ಇದೇ ನಾವು ಆರಂಭಿಸಿದ ಸಮಸ್ಯೆ. ದಾಖಲೆಗಳು ಎಲ್ಲವೂ ಇದ್ದವು - ಲಕ್ಷಾಂತರ, ಜಿಲ್ಲೆಗಳಾದ್ಯಂತ. ಆದರೆ ಮುಖ್ಯವಾದ ವಿಷಯ - ಒಂದೇ ವ್ಯಕ್ತಿ, ಒಂದೇ ಬೈಕ್ ಅಥವಾ ಒಂದೇ UPI ಖಾತೆ ಮೂರು ಬೇರೆ ಠಾಣೆಗಳ ಪ್ರಕರಣಗಳಲ್ಲಿ ಕಾಣಿಸಿಕೊಂಡಿರುವುದು - ಯಾರಿಗೂ ಪಕ್ಕಪಕ್ಕ ಓದಲು ಸಮಯವಿಲ್ಲದ ಪಠ್ಯದಲ್ಲಿ ಹುದುಗಿತ್ತು. ಕೈಯಾರೆ ಹುಡುಕಲು ಗಂಟೆಗಳು ಬೇಕಾಗುತ್ತಿದ್ದವು, ಮತ್ತು ದತ್ತಾಂಶಕ್ಕೆ ನೇರ ಪ್ರವೇಶ ಕೊಡುವುದು ಸುರಕ್ಷಿತವಲ್ಲ. ಹಾಗಾಗಿ ನಾವು Antar ನಿರ್ಮಿಸಿದೆವು: FIR ಗಳನ್ನು ಒಟ್ಟಿಗೆ ಓದುವ, ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಉತ್ತರಿಸುವ, ಮತ್ತು ಪ್ರತಿ ಉತ್ತರದ ಹಿಂದಿನ ದಾಖಲೆಗಳನ್ನು ತೋರಿಸುವ ವ್ಯವಸ್ಥೆ."
                : "That was the problem we started with. The records were all there, lakhs of them, spread across districts. But the part that mattered, that the same man, the same bike or the same UPI account had turned up in cases at three different stations, sat inside text nobody had time to read side by side. Looking it up by hand took hours, and giving people direct access to the database was never going to be safe. So we built Antar: something that reads across the FIRs for you, answers in Kannada or English, and shows you the records behind every answer."}
            </p>
          </section>

          <section className="ab-card">
            <div className="ab-sec-label">
              {kn ? "ನಮ್ಮ ದೃಷ್ಟಿಕೋನ" : "OUR VISION"}
            </div>
            <div className="ab-vision-list">
              <div className="ab-vision-row">
                <strong>{kn ? "ಪ್ರಕರಣಗಳನ್ನು ಒಟ್ಟಿಗೆ ಯೋಚಿಸುವುದು" : "Thinking across cases"}</strong>
                <span>
                  {kn
                    ? "ಈಗಾಗಲೇ ದಾಖಲೆಯಲ್ಲಿರುವುದನ್ನು ಜೋಡಿಸುವುದು - ಒಂದೇ ವಿಧಾನ, ಒಂದೇ ಸಹ-ಆರೋಪಿ, ಒಂದೇ ಜಿಲ್ಲೆಯ ಪ್ರವೃತ್ತಿ - ಹೊಸ ಪ್ರಕರಣ ಶೂನ್ಯದಿಂದ ಆರಂಭವಾಗಬಾರದು."
                    : "Join up what is already on record, the same method, the same co-accused, the same district trend, so no case has to start from zero."}
                </span>
              </div>
              <div className="ab-vision-row">
                <strong>{kn ? "ನಿಜವಾದ ದತ್ತಾಂಶದೊಂದಿಗೆ ಸುರಕ್ಷಿತ" : "Safe with real data"}</strong>
                <span>
                  {kn
                    ? "ಪ್ರತಿ ಅಧಿಕಾರಿ ತಮ್ಮ ಹುದ್ದೆಗೆ ಅನುಮತಿಸಿದ್ದನ್ನು ಮಾತ್ರ ನೋಡುತ್ತಾರೆ, ಪ್ರಶ್ನೆಗಳು ಅನುಮೋದಿತ ದಾರಿಗಳಲ್ಲೇ ಹೋಗುತ್ತವೆ, ಪ್ರತಿ ಅಂಕಿಯೂ ತನ್ನ FIR ಗೆ ಹಿಂದಿರುಗುತ್ತದೆ, ಮತ್ತು ಪ್ರತಿ ಬಳಕೆ ದಾಖಲಾಗುತ್ತದೆ."
                    : "Officers see only what their role allows, questions go through approved paths, every figure points back to its FIR, and every use is logged. Anything that changes things on the ground needs a second officer to say yes."}
                </span>
              </div>
              <div className="ab-vision-row">
                <strong>{kn ? "ಕ್ಷೇತ್ರದ ಅಧಿಕಾರಿಗಳಿಗಾಗಿ" : "Made for officers in the field"}</strong>
                <span>
                  {kn
                    ? "ಸಹೋದ್ಯೋಗಿಯನ್ನು ಕೇಳುವಂತೆಯೇ, ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಕೇಳಿ - ಕೆಲವೇ ಸೆಕೆಂಡುಗಳಲ್ಲಿ ದಾಖಲೆಗಳು ಸಿಗುತ್ತವೆ."
                    : "Ask the way you would ask a colleague, in Kannada or English, typed or spoken, and have the records in front of you in seconds."}
                </span>
              </div>
            </div>
          </section>
        </div>

        {/* Bottom Grid: Team Members */}
        <section className="ab-team-section">
          <div className="ab-sec-label">
            {kn ? "ತಂಡದ ಸದಸ್ಯರು" : "TEAM MEMBERS"}
          </div>
          <div className="ab-team-grid">
            {[
              {
                initials: "HD", name: "Harsha D B",
                role: ["Team Lead · Full-stack & security engineering", "ತಂಡದ ನಾಯಕ · ಫುಲ್-ಸ್ಟ್ಯಾಕ್ ಮತ್ತು ಭದ್ರತಾ ಇಂಜಿನಿಯರಿಂಗ್"],
                bio: ["Leads the team and owns how Antar thinks and how it stays safe. Every answer an officer reads has passed through his pipeline first.",
                      "ತಂಡವನ್ನು ಮುನ್ನಡೆಸುತ್ತಾರೆ; Antar ಹೇಗೆ ಯೋಚಿಸುತ್ತದೆ ಮತ್ತು ಹೇಗೆ ಸುರಕ್ಷಿತವಾಗಿರುತ್ತದೆ ಎಂಬುದು ಅವರ ಜವಾಬ್ದಾರಿ. ಅಧಿಕಾರಿ ಓದುವ ಪ್ರತಿ ಉತ್ತರವೂ ಮೊದಲು ಅವರ ವ್ಯವಸ್ಥೆಯ ಮೂಲಕ ಹಾದುಹೋಗುತ್ತದೆ."],
                built: [
                  ["The agents that work out each answer, and the checks that stop a wrong figure reaching an officer", "ಪ್ರತಿ ಉತ್ತರವನ್ನು ಲೆಕ್ಕ ಹಾಕುವ ಏಜೆಂಟ್‌ಗಳು, ಮತ್ತು ತಪ್ಪು ಅಂಕಿ ಅಧಿಕಾರಿಯನ್ನು ತಲುಪದಂತೆ ತಡೆಯುವ ಪರಿಶೀಲನೆಗಳು"],
                  ["Approved query paths over the FIR register, so nobody runs free-form queries on police data", "FIR ದಾಖಲೆಯ ಮೇಲೆ ಅನುಮೋದಿತ ಪ್ರಶ್ನೆ ದಾರಿಗಳು - ಪೊಲೀಸ್ ದತ್ತಾಂಶದ ಮೇಲೆ ಮುಕ್ತ ಪ್ರಶ್ನೆಗಳಿಲ್ಲ"],
                  ["Two-officer approvals and the audit record behind every action", "ಎರಡು-ಅಧಿಕಾರಿ ಅನುಮೋದನೆ ಮತ್ತು ಪ್ರತಿ ಕ್ರಮದ ಹಿಂದಿನ ಆಡಿಟ್ ದಾಖಲೆ"],
                ],
                focus: ["Backend · Security · Agents · Data", "ಬ್ಯಾಕೆಂಡ್ · ಭದ್ರತೆ · ಏಜೆಂಟ್‌ಗಳು · ದತ್ತಾಂಶ"],
              },
              {
                initials: "CM", name: "Chandana M",
                role: ["System design & frontend engineering", "ಸಿಸ್ಟಮ್ ವಿನ್ಯಾಸ ಮತ್ತು ಫ್ರಂಟ್-ಎಂಡ್ ಇಂಜಿನಿಯರಿಂಗ್"],
                bio: ["Owns everything an officer sees and touches, and makes complicated data feel calm and easy to read, even at the end of a long shift.",
                      "ಅಧಿಕಾರಿ ನೋಡುವ ಮತ್ತು ಬಳಸುವ ಎಲ್ಲವೂ ಅವರ ಜವಾಬ್ದಾರಿ; ಜಟಿಲ ದತ್ತಾಂಶವನ್ನೂ ದೀರ್ಘ ಶಿಫ್ಟ್‌ನ ಕೊನೆಯಲ್ಲೂ ಶಾಂತವಾಗಿ, ಸುಲಭವಾಗಿ ಓದುವಂತೆ ಮಾಡುತ್ತಾರೆ."],
                built: [
                  ["The Brain, Map, Predict and Search screens officers work in", "ಅಧಿಕಾರಿಗಳು ಕೆಲಸ ಮಾಡುವ ಬ್ರೈನ್, ನಕ್ಷೆ, ಮುನ್ಸೂಚನೆ ಮತ್ತು ಹುಡುಕಾಟ ಪರದೆಗಳು"],
                  ["The Kannada and English interface, from labels to fonts", "ಲೇಬಲ್‌ಗಳಿಂದ ಅಕ್ಷರಶೈಲಿಯವರೆಗೆ ಕನ್ನಡ ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಇಂಟರ್ಫೇಸ್"],
                  ["The layout that keeps each screen readable, with one clear next step", "ಪ್ರತಿ ಪರದೆಯನ್ನು ಓದಲು ಸುಲಭವಾಗಿಸುವ, ಒಂದು ಸ್ಪಷ್ಟ ಮುಂದಿನ ಹೆಜ್ಜೆಯ ವಿನ್ಯಾಸ"],
                ],
                focus: ["Frontend · System design · Maps · Bilingual UI", "ಫ್ರಂಟ್-ಎಂಡ್ · ಸಿಸ್ಟಮ್ ವಿನ್ಯಾಸ · ನಕ್ಷೆಗಳು · ದ್ವಿಭಾಷಾ UI"],
              },
            ].map((m) => (
              <article key={m.name} className="ab-member">
                <header className="ab-member-top">
                  <div className="ab-avatar">{m.initials}</div>
                  <div>
                    <h3 className="ab-member-name">{m.name}</h3>
                    <span className="ab-member-role">{kn ? m.role[1] : m.role[0]}</span>
                  </div>
                </header>
                <p className="ab-member-bio">{kn ? m.bio[1] : m.bio[0]}</p>
                <div className="ab-member-built">
                  <span>{kn ? "ನಿರ್ಮಿಸಿದ್ದು" : "What they built"}</span>
                  <ol>{m.built.map((b, n) => <li key={n}><em>{String(n + 1).padStart(2, "0")}</em>{kn ? b[1] : b[0]}</li>)}</ol>
                </div>
                <p className="ab-member-focus">{kn ? m.focus[1] : m.focus[0]}</p>
              </article>
            ))}
          </div>
        </section>

        {/* Compact Footer */}
        <footer className="ab-footer">
          <span>
            {kn
              ? "ಟೀಮ್ ವಿಮರಕ್ಷ · ಡೇಟಾಥಾನ್ 2026"
              : "Team Vimaraksha · Datathon 2026"}
          </span>
          <div className="ab-footer-links">
            <Link href="/docs">
              {kn ? "ದಾಖಲಾತಿ" : "Documentation"} <ArrowUpRight size={13} />
            </Link>
            <Link href="/antar">
              {kn ? "Antar ತೆರೆಯಿರಿ" : "Open Antar"} <ArrowUpRight size={13} />
            </Link>
          </div>
        </footer>

      </main>
    </div>
  );
}


