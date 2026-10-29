"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Entry gate - routes directly to login screen on initial localhost load
export default function EntryGate() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/login");
  }, [router]);

  return <div className="lg-gate" aria-hidden="true"><div className="signal-pulse" /></div>;
}
