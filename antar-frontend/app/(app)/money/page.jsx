"use client";
// The Money trail lives in Search now (/search?view=money). This keeps old links working.
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function MoneyRedirect() {
  const router = useRouter();
  const sp = useSearchParams();
  useEffect(() => {
    const a = sp?.get("account");
    router.replace(`/search?view=money${a ? `&account=${encodeURIComponent(a)}` : ""}`);
  }, [router, sp]);
  return null;
}
