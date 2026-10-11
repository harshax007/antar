"use client";

// The fifteen agents, in a line above the chat box.
//
// Each is its page-mascot character and nothing else - no disc, no card. At rest they are
// small; the one under the pointer (or focused from the keyboard) grows and shows its name
// and what it does. The sheets here are the small copies in public/mascots/sm: thirty
// full-size sheets would put 5 MB on the first screen an officer opens on a phone.
// Styles are in app/globals.css (.ags): an inline <style> here is escaped differently on
// the server and in the browser, which breaks hydration of the whole page.

import { Mascot } from "page-mascot";

// What each agent does, in the words of AGENTS.md. The nine that also walk the Brain
// screen keep the character they have there.
const AGENTS = [
  ["Query", "tv", "Answers from the FIR registry through fixed, checked queries."],
  ["Network", "gearbot", "Builds the links around a suspect."],
  ["Profile", "scout", "Scores a suspect's risk and shows what drives it."],
  ["Forecast", "clockwork", "Expected FIRs for the next week, with a range."],
  ["Social", "toaster", "Aggregate demographic patterns, never an individual."],
  ["Geo", "drone", "Hotspots, and where the load sits."],
  ["Pattern", "radio", "Recurring methods across cases."],
  ["Alerts", "lantern", "Flags unusual spikes and suggests patrols for approval."],
  ["OSINT", "rocket", "Open-web scan, always labelled unverified."],
  ["Research", "postbot", "A dossier of what is known, derived, inferred and unknown."],
  ["Recall", "crt", "Finds similar past FIRs."],
  ["Adversary", "knight", "Tests a hypothesis against its base rate before it is confirmed."],
  ["Vigil", "owl", "Screens a request for bias and legal compliance."],
  ["Corridor", "astronaut", "Movement of the same accused across districts."],
  ["Linkage", "cube", "Matches cases that share a vehicle, phone, UPI or IP."],
];

export default function AgentStrip() {
  return (
    <div className="ags" role="list" aria-label="Antar's agents">
      {AGENTS.map(([name, face, does]) => (
        <div key={name} className="ags-a" role="listitem" aria-label={`${name}: ${does}`}>
          <Mascot className="ags-f" size={40} label={`${name} agent`}
                  directions={`/mascots/sm/${face}-directions.webp`} reactions={`/mascots/sm/${face}-reactions.webp`} />
          <span className="ags-t"><b>{name}</b>{does}</span>
        </div>
      ))}
    </div>
  );
}
