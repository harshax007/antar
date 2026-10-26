"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Any address that is not a page goes to the home page, which sends the officer on to
// sign-in or Chat. The static export also writes this as 404.html, which is what the
// host serves for an unknown URL; scripts/postexport.mjs replaces that file with a plain
// redirect so it works before any script bundle loads.
export default function NotFound() {
  const router = useRouter();
  useEffect(() => { router.replace("/"); }, [router]);
  return <div className="lg-gate" aria-hidden="true"><div className="signal-pulse" /></div>;
}
