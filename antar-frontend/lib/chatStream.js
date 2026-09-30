// Shared SSE chat-stream client for /antar (chat) and /docs (live briefing).
// Mirrors the backend contract in app/api/chat_stream.py.

export const API = (process.env.NEXT_PUBLIC_API_URL || "");

export function newAssistantMsg(lang) {
  return {
    role: "assistant",
    lang,
    streaming: true,
    steps: [],
    text: "",
    citations: [],
    custody: null,
    confidence: null,
    brainBanner: null,
    brainHits: [],
    visuals: {},
    suspects: [],
    actions: [],
    suggested: [],
    template: null,
    reasoning: [],
    whyOpen: false,
    error: false,
    retryText: null,
    command: null,
  };
}

export function applyEvent(msg, evt) {
  switch (evt.type) {
    case "step": {
      const steps = [...msg.steps];
      const i = steps.findIndex((s) => s.agent === evt.agent);
      const step = { agent: evt.agent, status: evt.status, label: evt.label };
      if (i >= 0) steps[i] = step; else steps.push(step);
      return { ...msg, steps };
    }
    case "token":
      return { ...msg, text: msg.text + evt.content };
    case "citations":
      return { ...msg, citations: evt.data || [] };
    case "brain_hits":
      return { ...msg, brainHits: evt.data || [], brainBanner: evt.banner || msg.brainBanner };
    case "visual":
      return { ...msg, visuals: { ...msg.visuals, [evt.key]: evt.data } };
    case "confidence":
      return { ...msg, confidence: { routing: evt.routing, answer: evt.answer, label: evt.label } };
    case "actions":
      return { ...msg, actions: evt.data || [] };
    case "suggested":
      return { ...msg, suggested: evt.data || [] };
    case "layout":
      return { ...msg, layout: evt.data || null };
    case "custody":
      return { ...msg, custody: evt.data || null };
    case "complete":
      return {
        ...msg,
        streaming: false,
        lang: evt.lang || msg.lang,
        suspects: evt.suspects || [],
        template: evt.template_id,
        reasoning: evt.reasoning || [],
        command: evt.command || null,
        noResults: !!evt.no_results,
      };
    case "error":
      return { ...msg, streaming: false, error: true, text: msg.text || evt.message || "" };
    default:
      return msg;
  }
}

// POST /api/chat/stream and invoke onEvent(evt) per SSE event. Returns when the
// stream closes. Throws on transport/HTTP failure (caller decides the fallback).
export async function streamChat({ text, sessionId = null, lang = "en", deepThink = false, onEvent, signal }) {
  const res = await fetch(`${API}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang, session_id: sessionId, deep_think: deepThink }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += value;
    const parts = buf.split("\n\n");
    buf = parts.pop();
    for (const raw of parts) {
      if (!raw || raw.startsWith(":")) continue;
      const line = raw.replace(/^data: /, "").trim();
      if (!line) continue;
      let evt;
      try { evt = JSON.parse(line); } catch { continue; }
      onEvent(evt);
    }
  }
}

// The three brand slash commands surfaced in the chat input and on /docs.
export const SLASH_COMMANDS = [
  { cmd: "/think",      color: "#22E6F0", en: "Show the full reasoning trail behind the answer",           kn: "ಉತ್ತರದ ಹಿಂದಿನ ಸಂಪೂರ್ಣ ತರ್ಕವನ್ನು ತೋರಿಸಿ" },
  { cmd: "/connect",    color: "#10B981", en: "Force linkage agents - network & profile connections",      kn: "ಸಂಪರ್ಕ ಏಜೆಂಟ್‌ಗಳು - ನೆಟ್‌ವರ್ಕ್ ಮತ್ತು ಪ್ರೊಫೈಲ್" },
  { cmd: "/anticipate", color: "#F59E0B", en: "Force forecast agents - hotspots, prediction & patterns",   kn: "ಮುನ್ಸೂಚನಾ ಏಜೆಂಟ್‌ಗಳು - ಹಾಟ್‌ಸ್ಪಾಟ್ ಮತ್ತು ಭವಿಷ್ಯ" },
];


