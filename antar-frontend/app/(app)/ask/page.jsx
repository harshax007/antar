"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AskRedirect() {
  const router = useRouter();
  // /ask?q=... is the old address for "ask this in Chat": pass the question on, don't drop it.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    router.replace(q ? `/antar?q=${encodeURIComponent(q)}` : "/antar");
  }, [router]);
  return null;
}
