"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function GuideRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/docs");
  }, [router]);
  return null;
}
