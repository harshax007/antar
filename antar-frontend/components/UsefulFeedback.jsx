"use client";
// "Was this useful?" for a forecast, a shift plan or a lead. Yes is one click; No asks why,
// because the reason is the part worth reading. Sent to /api/forecast/feedback under the
// signed-in officer.
import { useState } from "react";
import { fetchAPI } from "@/lib/api";

export default function UsefulFeedback({ kind, unit, kn = false }) {
  const [state, setState] = useState("ask");       // ask | why | sent | failed
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState("");

  const send = async (useful) => {
    try {
      await fetchAPI("/api/forecast/feedback", { method: "POST", body: JSON.stringify({ kind, unit, useful, reason: useful ? "" : reason }) });
      setState("sent");
    } catch (e) {
      setMsg(kn
        ? (e?.status === 404 ? "ಅಭಿಪ್ರಾಯ ಲೋಡ್ ಆಗಲು ಸರ್ವರ್ ಮರುಆರಂಭಿಸಬೇಕು." : (e?.status === 422 ? "ಏಕೆ ಉಪಯುಕ್ತವಾಗಿಲ್ಲ ಎಂದು ಸಂಕ್ಷಿಪ್ತವಾಗಿ ಹೇಳಿ." : "ಉಳಿಸಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."))
        : (e?.status === 404 ? "Feedback needs the server restarted to load it." : (e?.status === 422 ? "Say briefly why it was not useful." : "It could not be saved. Try again.")));
      setState(e?.status === 422 ? "why" : "failed");
    }
  };

  if (state === "sent") return <p className="uf done">{kn ? "ದಾಖಲಿಸಲಾಗಿದೆ. ಧನ್ಯವಾದ." : "Recorded. Thank you."}</p>;
  return (
    <div className="uf">
      {state !== "why" ? (
        <>
          <span>{kn ? "ಇದು ಉಪಯುಕ್ತವೇ?" : "Was this useful?"}</span>
          <button type="button" onClick={() => send(true)}>{kn ? "ಹೌದು" : "Yes"}</button>
          <button type="button" onClick={() => { setMsg(""); setState("why"); }}>{kn ? "ಇಲ್ಲ" : "No"}</button>
        </>
      ) : (
        <>
          <label>
            <span>{kn ? "ಏನು ತಪ್ಪಾಗಿತ್ತು ಅಥವಾ ಕಾಣೆಯಾಗಿತ್ತು?" : "What was wrong or missing?"}</span>
            <input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} autoFocus
                   onKeyDown={(e) => { if (e.key === "Enter" && reason.trim().length >= 3) send(false); }} />
          </label>
          <button type="button" disabled={reason.trim().length < 3} onClick={() => send(false)}>{kn ? "ಕಳುಹಿಸಿ" : "Send"}</button>
          <button type="button" onClick={() => setState("ask")}>{kn ? "ರದ್ದು" : "Cancel"}</button>
        </>
      )}
      {msg && <em>{msg}</em>}
    </div>
  );
}
