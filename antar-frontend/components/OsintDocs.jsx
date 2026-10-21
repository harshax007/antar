"use client";

// What the open-source checks (OSINT) do: what an officer can check, what comes back, where it
// comes from, and what never leaves the building. Opened from "Know more" on the Search screen's
// OSINT consent card; its button starts the checks.

// Each list in English and Kannada: [en, kn].
const TYPES = {
  en: [["Phone number", "+91 98450 67890"], ["UPI ID", "9845012345@ybl"], ["Vehicle", "KA-02-MJ-4821"],
       ["Bank account", "30881234567 SBIN0040071"], ["IFSC", "SBIN0040071"], ["IMEI", "490154203237518"],
       ["Website", "sbi-rewards.online"], ["Email", "name@domain.in"], ["Username", "@handle"], ["Name", "Ramesh Gowda"]],
  kn: [["ಫೋನ್ ಸಂಖ್ಯೆ", "+91 98450 67890"], ["UPI ಐಡಿ", "9845012345@ybl"], ["ವಾಹನ", "KA-02-MJ-4821"],
       ["ಬ್ಯಾಂಕ್ ಖಾತೆ", "30881234567 SBIN0040071"], ["IFSC", "SBIN0040071"], ["IMEI", "490154203237518"],
       ["ವೆಬ್‌ಸೈಟ್", "sbi-rewards.online"], ["ಇಮೇಲ್", "name@domain.in"], ["ಬಳಕೆದಾರ ಹೆಸರು", "@handle"], ["ಹೆಸರು", "Ramesh Gowda"]],
};

const GET = {
  en: [
    ["Only real mentions",
     "The identifier is searched in each way it is written (98450 67890, 9845067890, +919845067890). A web page is shown only if it actually contains it, with what it matched on. Pages that don't are counted and left out, and \"nothing found\" is said plainly."],
    ["Checked live",
     "An IFSC gives the bank, branch, address and branch phone. A website gives when it was registered, by which registrar, and its certificate history; a site only weeks old is flagged. An IMEI's check digit is tested on the spot."],
    ["What to do next",
     "The official portal to check it on, what that portal tells you, and how to use it: the I4C Suspect Registry, Sanchar Saathi, eChallan, Vahan, eCourts and more."],
    ["A notice, drafted",
     "A Section 94 BNSS notice to whoever holds the records: the telecom operator, the bank (with a Section 106 freeze), the RTO, the domain registrar or the email provider. A name alone gets none: it has no record holder."],
  ],
  kn: [
    ["ನೈಜ ಉಲ್ಲೇಖಗಳು ಮಾತ್ರ",
     "ಗುರುತನ್ನು ಅದು ಬರೆಯುವ ಪ್ರತಿ ರೀತಿಯಲ್ಲೂ ಹುಡುಕಲಾಗುತ್ತದೆ (98450 67890, 9845067890, +919845067890). ಪುಟದಲ್ಲಿ ಅದು ನಿಜವಾಗಿ ಇದ್ದರೆ ಮಾತ್ರ ತೋರಿಸಲಾಗುತ್ತದೆ, ಯಾವುದಕ್ಕೆ ಹೊಂದಿತು ಎಂಬುದರೊಂದಿಗೆ. ಇಲ್ಲದ ಪುಟಗಳನ್ನು ಎಣಿಸಿ ಬಿಡಲಾಗುತ್ತದೆ; ಏನೂ ಸಿಗದಿದ್ದರೆ ಹಾಗೆಯೇ ಹೇಳಲಾಗುತ್ತದೆ."],
    ["ನೇರ ಪರಿಶೀಲನೆ",
     "IFSC ನಿಂದ ಬ್ಯಾಂಕ್, ಶಾಖೆ, ವಿಳಾಸ ಮತ್ತು ಶಾಖೆಯ ಫೋನ್. ವೆಬ್‌ಸೈಟ್ ಯಾವಾಗ, ಯಾವ ರಿಜಿಸ್ಟ್ರಾರ್ ಮೂಲಕ ನೋಂದಣಿಯಾಯಿತು ಮತ್ತು ಅದರ ಪ್ರಮಾಣಪತ್ರ ಇತಿಹಾಸ; ಕೆಲವೇ ವಾರಗಳ ಹಳೆಯ ತಾಣವನ್ನು ಗುರುತಿಸಲಾಗುತ್ತದೆ. IMEI ಯ ಪರಿಶೀಲನಾ ಅಂಕಿಯನ್ನು ತಕ್ಷಣ ಪರೀಕ್ಷಿಸಲಾಗುತ್ತದೆ."],
    ["ಮುಂದೆ ಏನು ಮಾಡಬೇಕು",
     "ಇದನ್ನು ಪರಿಶೀಲಿಸಬೇಕಾದ ಅಧಿಕೃತ ಪೋರ್ಟಲ್, ಅದು ಏನು ತಿಳಿಸುತ್ತದೆ ಮತ್ತು ಹೇಗೆ ಬಳಸುವುದು: I4C ಶಂಕಿತರ ದಾಖಲೆ, ಸಂಚಾರ ಸಾಥಿ, ಇ-ಚಲನ್, ವಾಹನ್, ಇ-ಕೋರ್ಟ್ಸ್ ಮತ್ತು ಇನ್ನಷ್ಟು."],
    ["ಕರಡು ನೋಟಿಸ್",
     "ದಾಖಲೆ ಹೊಂದಿರುವವರಿಗೆ BNSS ಸೆಕ್ಷನ್ 94 ನೋಟಿಸ್: ದೂರಸಂಪರ್ಕ ಸಂಸ್ಥೆ, ಬ್ಯಾಂಕ್ (ಸೆಕ್ಷನ್ 106 ಹಣ ತಡೆ ಸಹಿತ), RTO, ಡೊಮೇನ್ ರಿಜಿಸ್ಟ್ರಾರ್ ಅಥವಾ ಇಮೇಲ್ ಸೇವೆ. ಕೇವಲ ಹೆಸರಿಗೆ ನೋಟಿಸ್ ಇಲ್ಲ: ಅದಕ್ಕೆ ದಾಖಲೆ ಹೊಂದಿರುವವರಿಲ್ಲ."],
  ],
};

const LIVE = {
  en: [
    ["RBI IFSC list", "Bank branch, address, phone, UPI / IMPS support", "IFSC, bank account"],
    ["Domain registry (RDAP / WHOIS)", "Registration date, age, registrar, name servers", "Website, email domain"],
    ["Certificate log (crt.sh)", "Certificates ever issued, sister site names", "Website"],
    ["IMEI check digit", "Whether the IMEI is well-formed (worked out here, nothing sent)", "IMEI"],
    ["Open-web search", "Pages that contain the identifier", "Every type"],
  ],
  kn: [
    ["RBI IFSC ಪಟ್ಟಿ", "ಬ್ಯಾಂಕ್ ಶಾಖೆ, ವಿಳಾಸ, ಫೋನ್, UPI / IMPS ಸೌಲಭ್ಯ", "IFSC, ಬ್ಯಾಂಕ್ ಖಾತೆ"],
    ["ಡೊಮೇನ್ ನೋಂದಣಿ (RDAP / WHOIS)", "ನೋಂದಣಿ ದಿನಾಂಕ, ವಯಸ್ಸು, ರಿಜಿಸ್ಟ್ರಾರ್, ನೇಮ್ ಸರ್ವರ್‌ಗಳು", "ವೆಬ್‌ಸೈಟ್, ಇಮೇಲ್ ಡೊಮೇನ್"],
    ["ಪ್ರಮಾಣಪತ್ರ ದಾಖಲೆ (crt.sh)", "ನೀಡಲಾದ ಪ್ರಮಾಣಪತ್ರಗಳು, ಸಂಬಂಧಿತ ತಾಣಗಳ ಹೆಸರುಗಳು", "ವೆಬ್‌ಸೈಟ್"],
    ["IMEI ಪರಿಶೀಲನಾ ಅಂಕಿ", "IMEI ಸರಿಯಾದ ರೂಪದಲ್ಲಿದೆಯೇ (ಇಲ್ಲೇ ಲೆಕ್ಕಿಸಲಾಗುತ್ತದೆ, ಏನೂ ಕಳುಹಿಸುವುದಿಲ್ಲ)", "IMEI"],
    ["ಮುಕ್ತ-ವೆಬ್ ಹುಡುಕಾಟ", "ಗುರುತನ್ನು ಹೊಂದಿರುವ ಪುಟಗಳು", "ಎಲ್ಲ ಪ್ರಕಾರಗಳು"],
  ],
};

const OFFICIAL = {
  en: [
    ["I4C Suspect Registry", "Cyber-fraud complaints anywhere in India", "Phone, UPI, account, email, website"],
    ["Sanchar Saathi: CEIR, Know Your Mobile, Chakshu", "Stolen-phone block, make and model, fraud-call reporting", "IMEI, phone"],
    ["eChallan and Vahan", "Where the vehicle was caught on camera; the registration record", "Vehicle"],
    ["eCourts, Indian Kanoon, MCA", "Cases, judgments and bail orders; companies and directors", "Name"],
    ["NCRP / 1930", "Hold on money just lost to fraud", "UPI, bank account"],
    ["URLhaus, Wayback Machine", "Malware reports; how the site looked before it was taken down", "Website"],
  ],
  kn: [
    ["I4C ಶಂಕಿತರ ದಾಖಲೆ", "ಭಾರತದಾದ್ಯಂತ ಸೈಬರ್-ವಂಚನೆ ದೂರುಗಳು", "ಫೋನ್, UPI, ಖಾತೆ, ಇಮೇಲ್, ವೆಬ್‌ಸೈಟ್"],
    ["ಸಂಚಾರ ಸಾಥಿ: CEIR, KYM, ಚಕ್ಷು", "ಕಳುವಾದ ಫೋನ್ ತಡೆ, ಮಾದರಿ, ವಂಚನೆ ಕರೆ ವರದಿ", "IMEI, ಫೋನ್"],
    ["ಇ-ಚಲನ್ ಮತ್ತು ವಾಹನ್", "ವಾಹನ ಕ್ಯಾಮೆರಾದಲ್ಲಿ ಎಲ್ಲಿ ಸಿಕ್ಕಿತು; ನೋಂದಣಿ ದಾಖಲೆ", "ವಾಹನ"],
    ["ಇ-ಕೋರ್ಟ್ಸ್, ಇಂಡಿಯನ್ ಕಾನೂನ್, MCA", "ಪ್ರಕರಣಗಳು, ತೀರ್ಪುಗಳು, ಜಾಮೀನು ಆದೇಶಗಳು; ಕಂಪನಿಗಳು ಮತ್ತು ನಿರ್ದೇಶಕರು", "ಹೆಸರು"],
    ["NCRP / 1930", "ವಂಚನೆಯಲ್ಲಿ ಕಳೆದ ಹಣಕ್ಕೆ ತಡೆ", "UPI, ಬ್ಯಾಂಕ್ ಖಾತೆ"],
    ["URLhaus, ವೇಬ್ಯಾಕ್ ಮೆಷಿನ್", "ಮಾಲ್‌ವೇರ್ ವರದಿಗಳು; ತೆಗೆದುಹಾಕುವ ಮೊದಲು ತಾಣ ಹೇಗಿತ್ತು", "ವೆಬ್‌ಸೈಟ್"],
  ],
};

const SAFE = {
  en: [
    "Only the identifier leaves the building. No case text, and nothing from an FIR, is ever sent.",
    "It never reads or changes the FIR record. Everything found is an unverified lead until an officer confirms it.",
    "Every search is logged against the officer who ran it, and every outside call is on the outbound-call list.",
    "Official portals are opened by the officer in their own login. Antar does not sign in to them or copy them.",
  ],
  kn: [
    "ಗುರುತು ಮಾತ್ರ ಹೊರಗೆ ಹೋಗುತ್ತದೆ. ಪ್ರಕರಣದ ಪಠ್ಯ ಅಥವಾ FIR ನ ಯಾವುದೂ ಕಳುಹಿಸಲಾಗುವುದಿಲ್ಲ.",
    "FIR ದಾಖಲೆಯನ್ನು ಓದುವುದಿಲ್ಲ, ಬದಲಿಸುವುದಿಲ್ಲ. ಅಧಿಕಾರಿ ದೃಢೀಕರಿಸುವವರೆಗೆ ಸಿಕ್ಕಿದ್ದೆಲ್ಲವೂ ಪರಿಶೀಲಿಸದ ಸುಳಿವು.",
    "ಪ್ರತಿ ಹುಡುಕಾಟವನ್ನು ನಡೆಸಿದ ಅಧಿಕಾರಿಯ ಹೆಸರಿನಲ್ಲಿ ದಾಖಲಿಸಲಾಗುತ್ತದೆ; ಪ್ರತಿ ಹೊರಗಿನ ಕರೆ ಅನುಮತಿ ಪಟ್ಟಿಯಲ್ಲಿರುತ್ತದೆ.",
    "ಅಧಿಕೃತ ಪೋರ್ಟಲ್‌ಗಳನ್ನು ಅಧಿಕಾರಿ ತಮ್ಮ ಲಾಗಿನ್‌ನಲ್ಲಿ ತೆರೆಯುತ್ತಾರೆ. ಅಂತರ್ ಅವುಗಳಿಗೆ ಲಾಗಿನ್ ಆಗುವುದಿಲ್ಲ, ನಕಲಿಸುವುದಿಲ್ಲ.",
  ],
};

const SAMPLE = {
  en: [
    ["WHAT IT IS", "A bank account at State Bank of India, Mirle branch, Mysore (IFSC SBIN0040071)."],
    ["OPEN WEB", "No public page mentions it: 10 pages checked, none contains it."],
    ["CHECKED LIVE", "Bank branch found: State Bank of India, Mirle, Mysuru."],
    ["NEXT", "1. Address the bank notice to the nodal officer of SBI Mirle.  2. Check it on the I4C Suspect Registry.  3. If a victim has just paid, report on 1930 now."],
  ],
  kn: [
    ["ಇದು ಏನು", "ಸ್ಟೇಟ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ, ಮಿರ್ಲೆ ಶಾಖೆ, ಮೈಸೂರು (IFSC SBIN0040071) ಯಲ್ಲಿರುವ ಬ್ಯಾಂಕ್ ಖಾತೆ."],
    ["ಮುಕ್ತ ವೆಬ್", "ಯಾವುದೇ ಸಾರ್ವಜನಿಕ ಪುಟ ಇದನ್ನು ಉಲ್ಲೇಖಿಸಿಲ್ಲ: 10 ಪುಟ ಪರಿಶೀಲಿಸಲಾಗಿದೆ."],
    ["ನೇರ ಪರಿಶೀಲನೆ", "ಬ್ಯಾಂಕ್ ಶಾಖೆ ಸಿಕ್ಕಿದೆ: ಸ್ಟೇಟ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ, ಮಿರ್ಲೆ, ಮೈಸೂರು."],
    ["ಮುಂದೆ", "1. SBI ಮಿರ್ಲೆಯ ನೋಡಲ್ ಅಧಿಕಾರಿಗೆ ಬ್ಯಾಂಕ್ ನೋಟಿಸ್.  2. I4C ಶಂಕಿತರ ದಾಖಲೆಯಲ್ಲಿ ಪರಿಶೀಲಿಸಿ.  3. ಸಂತ್ರಸ್ತರು ಈಗಷ್ಟೇ ಹಣ ಕಳುಹಿಸಿದ್ದರೆ ತಕ್ಷಣ 1930 ಗೆ ವರದಿ ಮಾಡಿ."],
  ],
};

const WORDS = {
  types: ["What you can check", "ಏನನ್ನು ಪರಿಶೀಲಿಸಬಹುದು"],
  sees: ["What the officer sees first", "ಅಧಿಕಾರಿ ಮೊದಲು ನೋಡುವುದು"],
  seesFoot: ["Then the detail in tabs: open-web pages, checked live, official checks, what it decodes to, notice to send, profile links, step log. \"Copy lead sheet\" copies all of it for the case diary.",
             "ನಂತರ ಟ್ಯಾಬ್‌ಗಳಲ್ಲಿ ವಿವರ: ವೆಬ್ ಪುಟಗಳು, ನೇರ ಪರಿಶೀಲನೆ, ಅಧಿಕೃತ ಪರಿಶೀಲನೆ, ಇದರ ವಿವರ, ನೋಟಿಸ್, ಪ್ರೊಫೈಲ್ ಲಿಂಕ್‌ಗಳು, ಹಂತಗಳ ದಾಖಲೆ. \"ಸುಳಿವು ಪಟ್ಟಿ ನಕಲಿಸಿ\" ಎಲ್ಲವನ್ನೂ ಪ್ರಕರಣ ದಿನಚರಿಗಾಗಿ ನಕಲಿಸುತ್ತದೆ."],
  live: ["Checked live, automatically", "ನೇರವಾಗಿ, ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಪರಿಶೀಲನೆ"],
  official: ["Official checks, one click away", "ಅಧಿಕೃತ ಪರಿಶೀಲನೆ, ಒಂದೇ ಕ್ಲಿಕ್"],
  safe: ["What stays inside", "ಒಳಗೇ ಉಳಿಯುವುದು"],
  notUsed: ["Not used, on purpose: Truecaller or Facebook scraping (against their terms) and leaked databases (unlawful, and no use as evidence).",
            "ಉದ್ದೇಶಪೂರ್ವಕವಾಗಿ ಬಳಸುವುದಿಲ್ಲ: Truecaller ಅಥವಾ Facebook ಸ್ಕ್ರೇಪಿಂಗ್ (ಅವರ ನಿಯಮಗಳಿಗೆ ವಿರುದ್ಧ) ಮತ್ತು ಸೋರಿಕೆಯಾದ ಡೇಟಾಬೇಸ್‌ಗಳು (ಕಾನೂನುಬಾಹಿರ, ಸಾಕ್ಷ್ಯವಾಗಿ ಉಪಯೋಗವಿಲ್ಲ)."],
  hLive: [["Source", "Tells you", "For"], ["ಮೂಲ", "ತಿಳಿಸುವುದು", "ಯಾವುದಕ್ಕೆ"]],
  hOff: [["Portal", "Tells you", "For"], ["ಪೋರ್ಟಲ್", "ತಿಳಿಸುವುದು", "ಯಾವುದಕ್ಕೆ"]],
};

const S = {
  wrap: { margin: "20px auto 8px", maxWidth: 1100, display: "grid", gap: 22 },
  kicker: { fontFamily: "'JetBrains Mono', monospace", fontSize: 10, letterSpacing: "0.14em", color: "#22E6F0", textTransform: "uppercase" },
  h2: { fontFamily: "'Chakra Petch', sans-serif", fontSize: "clamp(22px, 3.4vw, 30px)", fontWeight: 700, color: "#F8FAFC", margin: "6px 0 10px" },
  lead: { fontSize: 14, lineHeight: 1.65, color: "#94A3B8", maxWidth: 760, margin: 0 },
  h3: { fontFamily: "'Chakra Petch', sans-serif", fontSize: 15, fontWeight: 700, color: "#E2E8F0", margin: "0 0 10px", letterSpacing: "0.02em" },
  card: { background: "rgba(3,6,15,0.7)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: "16px 18px" },
  chip: { display: "inline-flex", alignItems: "baseline", gap: 8, padding: "6px 11px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.03)", fontSize: 12.5, color: "#E2E8F0" },
  mono: { fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, color: "#64748B" },
  th: { textAlign: "left", fontSize: 10.5, fontWeight: 600, color: "#8FA3BC", padding: "6px 10px", borderBottom: "1px solid rgba(255,255,255,0.08)", textTransform: "uppercase", letterSpacing: "0.05em" },
  td: { fontSize: 12.5, color: "#CBD5E1", padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.05)", verticalAlign: "top", lineHeight: 1.5 },
};

function Table({ head, rows }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 520 }}>
        <thead><tr>{head.map((h) => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((r) => <tr key={r[0]}>{r.map((c, i) => <td key={i} style={{ ...S.td, ...(i === 0 ? { color: "#F1F5F9", fontWeight: 600 } : {}) }}>{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export default function OsintDocs({ kn = false, onTry, tryLabel }) {
  const L = kn ? "kn" : "en";
  const w = (k) => WORDS[k][kn ? 1 : 0];
  return (
    <section id="osint" style={S.wrap} aria-labelledby="osint-h">
      <div style={{ textAlign: "center", display: "grid", justifyItems: "center" }}>
        <span style={S.kicker}>{kn ? "ಹುಡುಕಾಟ · ಮುಕ್ತ ಮೂಲ ಪರಿಶೀಲನೆ" : "Search · Open-source checks"}</span>
        <h2 id="osint-h" style={S.h2}>{kn ? "ಒಂದು ಗುರುತು ಒಳಗೆ, ಕ್ರಮಕ್ಕೆ ಸಿದ್ಧ ಸುಳಿವು ಹೊರಗೆ." : "One identifier in. A lead sheet an officer can act on, out."}</h2>
        <p style={S.lead}>
          {kn
            ? "ಫೋನ್, UPI, ವಾಹನ, ಬ್ಯಾಂಕ್ ಖಾತೆ, IFSC, IMEI, ವೆಬ್‌ಸೈಟ್, ಇಮೇಲ್ ಅಥವಾ ಹೆಸರು: ಅದು ಏನು, ಮುಕ್ತ ವೆಬ್ ನಿಜವಾಗಿ ಏನು ಹೇಳುತ್ತದೆ, ನೇರ ದಾಖಲೆ ಪರಿಶೀಲನೆ, ಮುಂದೆ ಏನು ಮಾಡಬೇಕು, ಮತ್ತು ಕರಡು ನೋಟಿಸ್."
            : "Type a phone number, UPI ID, vehicle, bank account, IFSC, IMEI, website, email or name. You get what it is, what the open web really says about it, live registry checks, the official checks to run next, and a drafted notice. When there is nothing, it says nothing was found instead of filling the screen."}
        </p>
      </div>

      <div style={S.card}>
        <h3 style={S.h3}>{w("types")}</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {TYPES[L].map(([t, ex]) => <span key={t} style={S.chip}>{t}<span style={S.mono}>{ex}</span></span>)}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
        {GET[L].map(([h, t], i) => (
          <div key={h} style={S.card}>
            <span style={{ ...S.mono, color: "#22E6F0" }}>0{i + 1}</span>
            <h3 style={{ ...S.h3, margin: "6px 0 6px" }}>{h}</h3>
            <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.6, color: "#B4C2D6" }}>{t}</p>
          </div>
        ))}
      </div>

      <div style={S.card}>
        <h3 style={S.h3}>{w("sees")}</h3>
        <dl style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: "6px 12px", margin: 0, fontSize: 13, lineHeight: 1.55, color: "#E2E8F0", fontFamily: "'Inter', sans-serif" }}>
          {SAMPLE[L].flatMap(([k, v]) => [
            <dt key={k} style={{ ...S.mono, paddingTop: 3 }}>{k}</dt>,
            <dd key={k + "-v"} style={{ margin: 0 }}>{v}</dd>,
          ])}
        </dl>
        <p style={{ margin: "10px 0 0", fontSize: 11.5, color: "#64748B" }}>{w("seesFoot")}</p>
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        <div style={S.card}>
          <h3 style={S.h3}>{w("live")}</h3>
          <Table head={w("hLive")} rows={LIVE[L]} />
        </div>
        <div style={S.card}>
          <h3 style={S.h3}>{w("official")}</h3>
          <Table head={w("hOff")} rows={OFFICIAL[L]} />
        </div>
      </div>

      <div style={{ ...S.card, borderColor: "rgba(34,230,240,0.18)" }}>
        <h3 style={S.h3}>{w("safe")}</h3>
        <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 13, lineHeight: 1.55, color: "#CBD5E1" }}>
          {SAFE[L].map((s) => <li key={s}>{s}</li>)}
        </ul>
        <p style={{ margin: "10px 0 0", fontSize: 11.5, color: "#64748B" }}>
          {w("notUsed")}
        </p>
      </div>

      <div style={{ textAlign: "center" }}>
        <button type="button" onClick={onTry}
          style={{ background: "transparent", color: "#22E6F0", border: "1px solid rgba(34,230,240,0.45)", padding: "10px 26px", borderRadius: 999, fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "'Chakra Petch', sans-serif", letterSpacing: "0.06em" }}>
          {tryLabel || (kn ? "ಅರ್ಥವಾಯಿತು · ಪ್ರಾರಂಭಿಸಿ" : "I understand · Start")}
        </button>
      </div>
    </section>
  );
}
