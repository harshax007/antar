"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip, Popup, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

export default function MapView({ crimeType = "" }) {
  const [clusters, setClusters] = useState([]);
  const [note, setNote] = useState("");
  const [contours, setContours] = useState(null);

  useEffect(() => {
    const q = crimeType ? `?crime_type=${crimeType}` : "";
    fetch(`${API}/api/map/hotspots${q}`)
      .then((r) => r.json())
      .then((d) => { setClusters(d.clusters || []); setNote(d.seasonal_note || ""); })
      .catch(() => {});
      
    fetch(`${API}/api/map/predicted${q}`)
      .then((r) => r.json())
      .then((d) => { setContours(d.contours || null); })
      .catch(() => {});
  }, [crimeType]);

  const geo = clusters.filter((c) => c.lat != null && c.lon != null);
  const max = Math.max(...geo.map((c) => c.weight || 0), 1);
  const center = geo.length ? [geo[0].lat, geo[0].lon] : [12.97, 77.59]; // Bengaluru default

  return (
    <div>
      <div style={{ height: 480, borderRadius: 10, overflow: "hidden", border: "1px solid var(--border)" }}>
        <MapContainer center={center} zoom={11} scrollWheelZoom style={{ height: "100%", width: "100%", background: "#0B1220" }}>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
            attribution="&copy; Esri"
          />
          {contours && (
            <GeoJSON
              data={contours}
              style={(feature) => ({
                color: feature.properties?.color || "#F97316",
                weight: 1.5,
                fillColor: feature.properties?.color || "#F97316",
                fillOpacity: feature.properties?.fillOpacity || 0.2
              })}
              onEachFeature={(feature, layer) => {
                const props = feature.properties || {};
                layer.bindPopup(
                  `<div style="color: #1e293b; font-family: sans-serif; font-size: 12px; line-height: 1.4;">` +
                  `<strong style="font-size: 13px; color: ${props.color || '#ef4444'};">` +
                  `Spatiotemporal Hotspot Area (${props.risk} Risk)</strong><br/>` +
                  `<hr style="margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;" />` +
                  `• Peak Hours: <b>${props.peak_time_of_day}</b><br/>` +
                  `• Peak Days: <b>${props.peak_day_of_week}</b><br/>` +
                  `• Incident Count: <b>${props.incident_count}</b>` +
                  `</div>`
                );
              }}
            />
          )}
          {geo.map((c, i) => {
            const t = c.weight / max;
            return (
              <CircleMarker key={i} center={[c.lat, c.lon]}
                radius={8 + t * 22}
                pathOptions={{ color: "#EF4444", weight: 1, fillColor: "#EF4444", fillOpacity: 0.2 + 0.55 * t }}>
                <Tooltip>{c.zone}: {c.weight}</Tooltip>
                <Popup><b>{c.zone}</b><br />{c.weight} incidents</Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
      {note && <div style={{ color: "var(--text-secondary)", fontSize: 12.5, marginTop: 8 }}>{note}</div>}
    </div>
  );
}


