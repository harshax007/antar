"use client";
import { Suspense } from "react";
import BrainHub from "@/components/BrainHub";

// Kept for deep links (Chat's Second-Brain CTA → /brain/structure?kpi=S0001);
// renders the same Screen 03 experience as /brain.
export default function BrainStructurePage() {
  return (
    <Suspense fallback={null}>
      <BrainHub />
    </Suspense>
  );
}
