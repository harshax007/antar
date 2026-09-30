"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function BrainStructureRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/antarBrain/structure");
  }, [router]);
  return null;
}
