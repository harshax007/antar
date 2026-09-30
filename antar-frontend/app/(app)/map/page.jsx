"use client";

import dynamic from "next/dynamic";

// Leaflet touches `window`, so the map is client-only (no SSR).
const MapScreen = dynamic(() => import("@/components/MapScreen"), {
  ssr: false,
  loading: () => <div className="mx-page" style={{ display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted)" }}>Loading map…</div>,
});

export default function MapPage() {
  return <MapScreen />;
}
