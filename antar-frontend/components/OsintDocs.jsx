"use client";

// Docs: the open-source checks (OSINT) on the Search screen - what an officer can check, what
// comes back, where it comes from, and what never leaves the building.

const TYPES = [
  ["Phone number", "+91 98450 67890"], ["UPI ID", "9845012345@ybl"], ["Vehicle", "KA-02-MJ-4821"],
  ["Bank account", "30881234567 SBIN0040071"], ["IFSC", "SBIN0040071"], ["IMEI", "490154203237518"],
  ["Website", "sbi-rewards.online"], ["Email", "name@domain.in"], ["Username", "@handle"], ["Name", "Ramesh Gowda"],
];

const GET = [
  ["Only real mentions",
   "The identifier is searched in each way it is written (98450 67890, 9845067890, +919845067890). A web page is shown only if it actually contains it, with what it matched on. Pages that don't are counted and left out, and \"nothing found\" is said plainly."],
  ["Checked live",
   "An IFSC gives the bank, branch, address and branch phone. A website gives when it was registered, by which registrar, and its certificate history; a site only weeks old is flagged. An IMEI's check digit is tested on the spot."],
  ["What to do next",
   "The official portal to check it on, what that portal tells you, and how to use it: the I4C Suspect Registry, Sanchar Saathi, eChallan, Vahan, eCourts and more."],
  ["A notice, drafted",
   "A Section 94 BNSS notice to whoever holds the records: the telecom operator, the bank (with a Section 106 freeze), the RTO, the domain registrar or the email provider. A name alone gets none: it has no record holder."],
];

const LIVE = [
  ["RBI IFSC list", "Bank branch, address, phone, UPI / IMPS support", "IFSC, bank account"],
  ["Domain registry (RDAP / WHOIS)", "Registration date, age, registrar, name servers", "Website, email domain"],
  ["Certificate log (crt.sh)", "Certificates ever issued, sister site names", "Website"],
  ["IMEI check digit", "Whether the IMEI is well-formed (worked out here, nothing sent)", "IMEI"],
  ["Open-web search", "Pages that contain the identifier", "Every type"],
];

const OFFICIAL = [
  ["I4C Suspect Registry", "Cyber-fraud complaints anywhere in India", "Phone, UPI, account, email, website"],
  ["Sanchar Saathi: CEIR, Know Your Mobile, Chakshu", "Stolen-phone block, make and model, fraud-call reporting", "IMEI, phone"],
  ["eChallan and Vahan", "Where the vehicle was caught on camera; the registration record", "Vehicle"],
  ["eCourts, Indian Kanoon, MCA", "Cases, judgments and bail orders; companies and directors", "Name"],
  ["NCRP / 1930", "Hold on money just lost to fraud", "UPI, bank account"],
  ["URLhaus, Wayback Machine", "Malware reports; how the site looked before it was taken down", "Website"],
];

const SAFE = [
  "Only the identifier leaves the building. No case text, and nothing from an FIR, is ever sent.",
  "It never reads or changes the FIR record. Everything found is an unverified lead until an officer confirms it.",
  "Every search is logged against the officer who ran it, and every outside call is on the outbound-call list.",
  "Official portals are opened by the officer in their own login. Antar does not sign in to them or copy them.",
];

const S = {
  wrap: { margin: "56px auto 8px", maxWidth: 1100, display: "grid", gap: 26 },
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

export default function OsintDocs({ kn = false, onTry }) {
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
        <h3 style={S.h3}>{kn ? "ಏನನ್ನು ಪರಿಶೀಲಿಸಬಹುದು" : "What you can check"}</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {TYPES.map(([t, ex]) => <span key={t} style={S.chip}>{t}<span style={S.mono}>{ex}</span></span>)}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
        {GET.map(([h, t], i) => (
          <div key={h} style={S.card}>
            <span style={{ ...S.mono, color: "#22E6F0" }}>0{i + 1}</span>
            <h3 style={{ ...S.h3, margin: "6px 0 6px" }}>{h}</h3>
            <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.6, color: "#B4C2D6" }}>{t}</p>
          </div>
        ))}
      </div>

      <div style={S.card}>
        <h3 style={S.h3}>{kn ? "ಫಲಿತಾಂಶ ಹೇಗೆ ಕಾಣುತ್ತದೆ" : "What the officer sees first"}</h3>
        <dl style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: "6px 12px", margin: 0, fontSize: 13, lineHeight: 1.55, color: "#E2E8F0", fontFamily: "'Inter', sans-serif" }}>
          {[
            ["WHAT IT IS", "A bank account at State Bank of India, Mirle branch, Mysore (IFSC SBIN0040071)."],
            ["OPEN WEB", "No public page mentions it: 10 pages checked, none contains it."],
            ["CHECKED LIVE", "Bank branch found: State Bank of India, Mirle, Mysuru."],
            ["NEXT", "1. Address the bank notice to the nodal officer of SBI Mirle.  2. Check it on the I4C Suspect Registry.  3. If a victim has just paid, report on 1930 now."],
          ].flatMap(([k, v]) => [
            <dt key={k} style={{ ...S.mono, paddingTop: 3 }}>{k}</dt>,
            <dd key={k + "-v"} style={{ margin: 0 }}>{v}</dd>,
          ])}
        </dl>
        <p style={{ margin: "10px 0 0", fontSize: 11.5, color: "#64748B" }}>Then the detail in tabs: open-web pages, checked live, official checks, what it decodes to, notice to send, profile links, step log. "Copy lead sheet" copies all of it for the case diary.</p>
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        <div style={S.card}>
          <h3 style={S.h3}>{kn ? "ನೇರ ಪರಿಶೀಲನೆ" : "Checked live, automatically"}</h3>
          <Table head={["Source", "Tells you", "For"]} rows={LIVE} />
        </div>
        <div style={S.card}>
          <h3 style={S.h3}>{kn ? "ಅಧಿಕೃತ ಪರಿಶೀಲನೆ" : "Official checks, one click away"}</h3>
          <Table head={["Portal", "Tells you", "For"]} rows={OFFICIAL} />
        </div>
      </div>

      <div style={{ ...S.card, borderColor: "rgba(34,230,240,0.18)" }}>
        <h3 style={S.h3}>{kn ? "ಸುರಕ್ಷತೆ" : "What stays inside"}</h3>
        <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 13, lineHeight: 1.55, color: "#CBD5E1" }}>
          {SAFE.map((s) => <li key={s}>{s}</li>)}
        </ul>
        <p style={{ margin: "10px 0 0", fontSize: 11.5, color: "#64748B" }}>
          Not used, on purpose: Truecaller or Facebook scraping (against their terms) and leaked databases (unlawful, and no use as evidence).
        </p>
      </div>

      <div style={{ textAlign: "center" }}>
        <button type="button" onClick={onTry}
          style={{ background: "transparent", color: "#22E6F0", border: "1px solid rgba(34,230,240,0.45)", padding: "10px 26px", borderRadius: 999, fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "'Chakra Petch', sans-serif", letterSpacing: "0.06em" }}>
          {kn ? "ಹುಡುಕಾಟದಲ್ಲಿ ಪ್ರಯತ್ನಿಸಿ →" : "Try it on Search →"}
        </button>
      </div>
    </section>
  );
}
