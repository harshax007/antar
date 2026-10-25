"use client";

// While the server is warming up, one quiet line at the top of every screen says so.
// Never "offline": the calls underneath are waiting for it and will go through on their own.

import { useEffect, useState } from "react";
import { checkServerOnce, getServerStatus, onServerStatus } from "@/lib/serverStatus";

export default function ServerWaking({ kn }) {
  const [status, setStatus] = useState(getServerStatus());
  const [since, setSince] = useState(null);
  const [, tick] = useState(0);

  useEffect(() => {
    const off = onServerStatus(setStatus);
    checkServerOnce();
    return off;
  }, []);

  useEffect(() => {
    if (status !== "waking") { setSince(null); return; }
    setSince(Date.now());
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [status]);

  if (status !== "waking") return null;
  const secs = since ? Math.floor((Date.now() - since) / 1000) : 0;
  return (
    <div className="ax-waking" role="status" aria-live="polite">
      <span className="dot" aria-hidden="true" />
      <span>
        {kn ? "ಅಂತರ್ ಸರ್ವರ್‌ನಲ್ಲಿ ಎಚ್ಚರಗೊಳ್ಳುತ್ತಿದೆ…" : "Antar is waking up on the server…"}
        <span className="sub">
          {kn
            ? " ಮೊದಲ ಬಾರಿ ಒಂದು ನಿಮಿಷ ತೆಗೆದುಕೊಳ್ಳಬಹುದು. ನಿಮ್ಮ ಪ್ರಶ್ನೆ ತಾನಾಗಿ ಮುಂದುವರಿಯುತ್ತದೆ."
            : " This can take a minute the first time. Your request will go through on its own."}
          {secs >= 5 ? ` · ${secs}s` : ""}
        </span>
      </span>
    </div>
  );
}
