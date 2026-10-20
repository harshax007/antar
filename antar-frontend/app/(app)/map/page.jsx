"use client";

import dynamic from "next/dynamic";
import BrainLoader, { MAP_STEPS, MAP_ORBS } from "@/components/BrainLoader";

// Leaflet touches `window`, so the map is client-only (no SSR).
const MapScreen = dynamic(() => import("@/components/MapScreen"), {
  ssr: false,
  loading: () => <div className="mx-page" style={{ position: "relative" }}><BrainLoader steps={MAP_STEPS} orbs={MAP_ORBS} /></div>,
});

export default function MapPage() {
  return <MapScreen />;
}
