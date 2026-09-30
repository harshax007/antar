"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function InfoRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/docs");
  }, [router]);
  return null;
}
