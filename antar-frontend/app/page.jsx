"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Entry gate - no session → /login, otherwise straight into Chat.
// Deliberately outside the (app)/(auth) groups so no chrome flashes before the redirect.
export default function EntryGate() {
  const router = useRouter();

  useEffect(() => {
    try {
      sessionStorage.removeItem("antar_session");
      localStorage.removeItem("antar_guide_seen");
    } catch {}
    router.replace("/login");
  }, [router]);

  return <div className="lg-gate" aria-hidden="true"><div className="signal-pulse" /></div>;
}
