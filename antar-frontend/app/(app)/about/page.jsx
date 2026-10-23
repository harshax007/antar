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
            <div className="ab-member">
              <div className="ab-avatar">HD</div>
              <div className="ab-member-body">
                <div className="ab-member-head">
                  <h3 className="ab-member-name">Harsha D B</h3>
                  <span className="ab-member-role">
                    {kn ? "ತಂಡದ ನಾಯಕ · ಫುಲ್-ಸ್ಟ್ಯಾಕ್ ಮತ್ತು ಸೆಕ್ಯುರಿಟಿ" : "Team Lead · Full-Stack & Security Engineering"}
                  </span>
                </div>
                <p className="ab-member-bio">
                  {kn
                    ? "Antar ನ ಹಿನ್ನೆಲೆ ವ್ಯವಸ್ಥೆಯನ್ನು ನಿರ್ಮಿಸಿದರು: ಉತ್ತರವನ್ನು ಲೆಕ್ಕ ಹಾಕುವ ಏಜೆಂಟ್‌ಗಳು, ಅವುಗಳನ್ನು ಪ್ರಾಮಾಣಿಕವಾಗಿಡುವ ನಿಯಮಗಳು, ಮತ್ತು FIR ದಾಖಲೆಯ ಮೇಲೆ ವೇಗದ, ಸುರಕ್ಷಿತ ಹುಡುಕಾಟ."
                    : "Built Antar's backend: the agents that work out each answer, the checks that keep them honest, and the fast, safe lookups over the FIR register."}
                </p>
              </div>
            </div>

            <div className="ab-member">
              <div className="ab-avatar">CM</div>
              <div className="ab-member-body">
                <div className="ab-member-head">
                  <h3 className="ab-member-name">Chandana M</h3>
                  <span className="ab-member-role">
                    {kn ? "ಸಿಸ್ಟಮ್ ವಿನ್ಯಾಸ ಮತ್ತು ಫ್ರಂಟ್-ಎಂಡ್ ಇಂಜಿನಿಯರಿಂಗ್" : "System Design & Frontend Engineering"}
                  </span>
                </div>
                <p className="ab-member-bio">
                  {kn
                    ? "ಅಧಿಕಾರಿಗಳು ನೋಡುವ ಎಲ್ಲವನ್ನೂ ವಿನ್ಯಾಸಗೊಳಿಸಿ ನಿರ್ಮಿಸಿದರು - ಹುಡುಕಾಟ, ಅಪರಾಧ ನಕ್ಷೆ, ಕನ್ನಡ ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಪರದೆಗಳು - ದತ್ತಾಂಶ ಜಟಿಲವಾಗಿದ್ದರೂ ಪರದೆ ಶಾಂತ ಮತ್ತು ಓದಲು ಸುಲಭ."
                    : "Designed and built what officers actually see, search, the crime map, the Kannada and English screens, and kept them calm and easy to read even when the data is not."}
                </p>
              </div>
            </div>
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


