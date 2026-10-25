"use client";
// Social insights live in Search now (/search?view=social). This keeps old links working.
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SocialRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/search?view=social"); }, [router]);
  return null;
}
