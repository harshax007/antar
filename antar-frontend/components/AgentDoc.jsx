"use client";

// One agent, on its own: what it does, how it works, what it refuses.
//
// Reached from the agent strip above the chat box (/docs?agent=Network). The steps, the
// refusal and the checks come from the backend's agent cards (GET /api/console/identity),
// so this page cannot describe an agent differently from the way it actually runs. Six of
// the fifteen have no console card; for those the page says what is known and no more.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Mascot } from "page-mascot";
import { asset } from "@/lib/assets";
import { fetchAPI } from "@/lib/api";
import { AGENTS, LENS } from "@/components/AgentStrip";

// The console card that belongs to each strip name, where one exists.
const CARD = { Network: "network", Profile: "profile", Research: "research", Adversary: "advocate", Recall: "recall",
               Linkage: "linkage", Forecast: "forecast", Geo: "geo", Pattern: "pattern" };
// Questions taken from the golden set (docs/golden_report.md): each is checked on every build.
const ASK = {
  Query: ["Which district has the most kidnapping cases?", "How many open cases by status?"],
  Network: ["Find suspect Yellappa", "Top suspects in Rajajinagar"],
  Profile: ["Who are the repeat offenders?"],
  Geo: ["Where are the theft hotspots?", "Top beats for theft in Bengaluru City"],
  Linkage: ["Which UPI IDs are used in more than one district?"],
  Social: ["Victim gender breakdown", "Age breakdown of suspects"],
};
const MODE_SAYS = {
  "/think": "Think: the answer with its full reasoning trail.",
  "/connect": "Connect: the linkage agents are brought in - network and profile connections.",
  "/anticipate": "Anticipate: the forecast agents are brought in - hotspots, prediction and patterns.",
};

export default function AgentDoc({ name }) {
  const router = useRouter();
  const [card, setCard] = useState(null);
  const agent = AGENTS.find(([n]) => n.toLowerCase() === String(name || "").toLowerCase());

  useEffect(() => {
    if (!agent || !CARD[agent[0]]) return;
    fetchAPI("/api/console/identity").then((p) => setCard((p.agents || []).find((a) => a.id === CARD[agent[0]]) || null)).catch(() => {});
  }, [name]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!agent) {
    return (
      <main className="adoc"><div className="adoc-in">
        <button className="adoc-back" onClick={() => router.push("/antar")}>← Back to chat</button>
        <h1>No agent called “{name}”</h1>
        <p className="adoc-lead">The agents are: {AGENTS.map(([n]) => n).join(", ")}.</p>
      </div></main>
    );
  }
  const [title, face, does] = agent;
  const mode = LENS[title];
  return (
    <main className="adoc">
      <div className="adoc-in">
        <button className="adoc-back" onClick={() => router.push("/antar")}>← Back to chat</button>
        <header>
          <Mascot size={112} label={`${title} agent`} directions={asset(`/mascots/sm/${face}-directions.webp`)} reactions={asset(`/mascots/sm/${face}-reactions.webp`)} />
          <div>
            <span>Antar agent</span>
            <h1>{title}</h1>
            <p className="adoc-lead">{card?.purpose || does}</p>
          </div>
        </header>

        <section>
          <h2>What it does</h2>
          <p>{does}</p>
          {card?.needs && <p className="adoc-dim">It works on {/^[aeiou]/i.test(card.needs) ? "an" : "a"} {card.needs}.</p>}
        </section>

        {card?.method?.length > 0 && (
          <section>
            <h2>How it works</h2>
            <ol>{card.method.map((m, i) => <li key={i}>{m}</li>)}</ol>
          </section>
        )}

        {card?.refuses && (
          <section>
            <h2>What it will not do</h2>
            <p>{card.refuses}</p>
          </section>
        )}

        {card?.guardrails?.length > 0 && (
          <section>
            <h2>Checks its output passes</h2>
            <p className="adoc-tags">{card.guardrails.map((g) => <code key={g}>{g}</code>)}</p>
          </section>
        )}

        <section>
          <h2>In chat</h2>
          <p>Pick {title} above the chat box and your first question is asked through <code>{mode}</code>. {MODE_SAYS[mode]}</p>
          {ASK[title] && <ul>{ASK[title].map((q) => <li key={q}>{q}</li>)}</ul>}
        </section>

        {!CARD[title] && (
          <p className="adoc-dim">{title} runs inside the answer pipeline and has no card of its own to run from the Brain screen, so its working steps are not listed here.</p>
        )}
      </div>
    </main>
  );
}
