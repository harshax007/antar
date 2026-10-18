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
            <p className="ab-lead">
              {kn
                ? "ಪೊಲೀಸ್ ತನಿಖೆ ಮತ್ತು ಸಾರ್ವಜನಿಕ ಸುರಕ್ಷತೆಗಾಗಿ ಪ್ರಾಯೋಗಿಕ ಹಾಗೂ ಸುರಕ್ಷಿತ ತಂತ್ರಜ್ಞಾನವನ್ನು ನಿರ್ಮಿಸುವ ಇಂಜಿನಿಯರಿಂಗ್ ತಂಡ."
                : "Building practical, secure intelligence tools for law enforcement and public safety."}
            </p>
          </div>

          <div className="ab-meaning">
            <div className="ab-meaning-title">
              {kn ? "‘ವಿಮರಕ್ಷ’ ಪದದ ಅರ್ಥ" : "Meaning of Vimaraksha"}
            </div>
            <p className="ab-meaning-text">
              {kn ? (
                <>
                  <b>ವಿಮರ್ಶೆ</b> (ಆಳವಾದ ಪರಿಶೀಲನೆ ಮತ್ತು ಚಿಂತನೆ) ಮತ್ತು <b>ರಕ್ಷೆ</b> (ಭದ್ರತೆ ಮತ್ತು ರಕ್ಷಣೆ) ಎಂಬ ಎರಡು ಪದಗಳಿಂದ <b>ವಿಮರಕ್ಷ</b> ಹುಟ್ಟಿದೆ. ದಾಖಲೆಗಳನ್ನು ಸೂಕ್ಷ್ಮವಾಗಿ ಪರಿಶೀಲಿಸಿ ಮುಂಚಿತವಾಗಿಯೇ ಸುರಕ್ಷತೆ ಒದಗಿಸುವುದು ಇದರ ಉದ್ದೇಶ.
                </>
              ) : (
                <>
                  Formed from <strong>Vimarsha</strong> (critical inquiry and reflection) and <strong>Raksha</strong> (protection and safeguarding). It stands for <em>protection through thoughtful inquiry</em>, examining records carefully to prevent harm early.
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
                ? "“ನಮ್ಮಲ್ಲಿ ಬೃಹತ್ ಪ್ರಮಾಣದ FIR ದತ್ತಾಂಶವಿದೆ, ಆದರೆ ಅದರ ಮೇಲೆ ಯೋಚಿಸುವ ಬುದ್ಧಿವಂತ ಪದರ ಇಲ್ಲ ಮತ್ತು ದತ್ತಾಂಶವನ್ನು ಸುರಕ್ಷಿತವಾಗಿ ಹುಡುಕಿ ತೆಗೆಯುವುದು ಸುಲಭವಲ್ಲ.”"
                : "“We have large data of FIRs, but no intelligent layer and thinking layer, and it is not easy to retrieve the data securely.”"}
            </blockquote>
            <p className="ab-card-text">
              {kn
                ? "ಪೊಲೀಸ್ ಇಲಾಖೆಗಳಲ್ಲಿ ಲಕ್ಷಾಂತರ FIR ದಾಖಲೆಗಳಿವೆ, ಆದರೆ ತನಿಖೆಯ ಸಮಯದಲ್ಲಿ ಪ್ರಕರಣಗಳ ನಡುವಿನ ನಂಟನ್ನು ಹುಡುಕುವುದು ಕಷ್ಟಕರವಾಗಿತ್ತು. ಈ ಸಮಸ್ಯೆಯನ್ನು ಪರಿಹರಿಸಲು ನಾವು Antar ಅನ್ನು ಅಭಿವೃದ್ಧಿಪಡಿಸಿದ್ದೇವೆ. ಇದು FIR ದತ್ತಾಂಶದ ಮೇಲೆ ಸುರಕ್ಷಿತ ಚಿಂತನಾ ಪದರವಾಗಿ ಕೆಲಸ ಮಾಡುತ್ತದೆ ಮತ್ತು ಅಧಿಕಾರಿಗಳಿಗೆ ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ತಕ್ಷಣವೇ ಪರಿಶೀಲಿಸಿದ ಮಾಹಿತಿಯನ್ನು ನೀಡುತ್ತದೆ."
                : "Police stations hold hundreds of thousands of FIRs across districts, yet important links between repeat offenders, vehicles, and crime patterns stay buried in static text. Manual lookup takes hours, and opening raw database access is unsafe. We developed Antar to solve this problem by adding a secure thinking and retrieval layer over FIR records."}
            </p>
          </section>

          <section className="ab-card">
            <div className="ab-sec-label">
              {kn ? "ನಮ್ಮ ದೃಷ್ಟಿಕೋನ" : "OUR VISION"}
            </div>
            <div className="ab-vision-list">
              <div className="ab-vision-row">
                <strong>{kn ? "ಬುದ್ಧಿವಂತ ವಿಶ್ಲೇಷಣಾ ಪದರ" : "Intelligent thinking layer"}</strong>
                <span>
                  {kn
                    ? "ಪ್ರಕರಣಗಳ ನಡುವಿನ ಸಂಬಂಧಗಳು, ಅಪರಾಧದ ಮಾದರಿಗಳು ಮತ್ತು ಸಹಚರರ ಜಾಲವನ್ನು ಗುರುತಿಸಿ ತನಿಖೆಗೆ ವೇಗ ನೀಡುವುದು."
                    : "Turn static FIR archives into active intelligence by connecting repeat modus operandi, co-accused networks, and district trends."}
                </span>
              </div>
              <div className="ab-vision-row">
                <strong>{kn ? "ಸುರಕ್ಷಿತ ಮಾಹಿತಿ ಪಡೆಯುವಿಕೆ" : "Secure data retrieval"}</strong>
                <span>
                  {kn
                    ? "ಹುದ್ದೆ ಆಧಾರಿತ ಪ್ರವೇಶ (RBAC) ಮತ್ತು ಲೆಕ್ಕಪರಿಶೋಧನಾ ದಾಖಲೆಯೊಂದಿಗೆ ಪ್ರತಿ ಅಂಕಿಅಂಶವೂ ಅಧಿಕೃತ FIR ಗೆ ಜೋಡಣೆಯಾಗಿರುತ್ತದೆ."
                    : "Enforce role-based permissions, approved query paths, and tamper-evident audit logs with every figure tied to its source FIR."}
                </span>
              </div>
              <div className="ab-vision-row">
                <strong>{kn ? "ಅಧಿಕಾರಿಗಳ ಭಾಷೆಯಲ್ಲೇ ಸಂವಹನ" : "Built for field officers"}</strong>
                <span>
                  {kn
                    ? "ಕನ್ನಡ ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಎರಡರಲ್ಲೂ ಸರಳವಾಗಿ ಪ್ರಶ್ನಿಸಿ ನಿಖರವಾದ ಉತ್ತರ ಪಡೆಯುವ ಸೌಲಭ್ಯ."
                    : "Support natural queries in Kannada and English so officers can move straight from a question to verified case records in seconds."}
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
                    ? "Antar ನ ಮೂಲ ವಾಸ್ತುಶಿಲ್ಪ, ಮಲ್ಟಿ-ಏಜೆಂಟ್ ಚಿಂತನಾ ವ್ಯವಸ್ಥೆ ಹಾಗೂ ಸುರಕ್ಷಿತ ಡೇಟಾ ಹುಡುಕಾಟದ ಪೈಪ್‌ಲೈನ್ ವಿನ್ಯಾಸಗೊಳಿಸಿದ್ದಾರೆ."
                    : "Architected Antar’s core backend, multi-agent reasoning pipeline, and security guardrails for fast, deterministic, and safe FIR retrieval."}
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
                    ? "ಅಧಿಕಾರಿಗಳ ತನಿಖಾ ಕಾರ್ಯಕ್ಷೇತ್ರ, ಅಪರಾಧ ನಕ್ಷೆಗಳು ಮತ್ತು ಕನ್ನಡ-ಇಂಗ್ಲಿಷ್ ಇಂಟರ್ಫೇಸ್ ಅನ್ನು ಸರಳ ಹಾಗೂ ಸ್ಪಷ್ಟವಾಗಿ ವಿನ್ಯಾಸಗೊಳಿಸಿದ್ದಾರೆ."
                    : "Designed and engineered the investigative workspace across search, spatial crime mapping, and bilingual views to keep complex data clear and minimal."}
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


