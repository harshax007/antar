"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AskRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/antar");
  }, [router]);
  return null;
}
