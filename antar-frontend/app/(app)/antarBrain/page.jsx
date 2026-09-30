"use client";
import { Suspense } from "react";
import BrainHub from "@/components/BrainHub";
import BrainLoader from "@/components/BrainLoader";

// Screen 03 · Brain - Page 01 (3D Brain Globe) + Page 02 (Data Overview).
// (The old KPI-tile BrainScreen is retired from the nav; /brain IS the globe now.)
const LoadingLine = () => <BrainLoader fullscreen />;

export default function BrainPage() {
  return (
    <Suspense fallback={<LoadingLine />}>
      <BrainHub />
    </Suspense>
  );
}
