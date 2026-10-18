"use client";

import { useEffect, useRef } from "react";

// 3D globe for the Map screen (globe.gl / three.js). Karnataka's district
// polygons are the only lit region on a dark sphere - choropleth fill by FIR
// load, Gi* hotspot points, hex-bin heat, pulsing patrol ring, and animated
// crime-flow arcs (cross-district offender corridors). Camera starts over
// Karnataka; slow auto-rotate until the user grabs it.
const KARNATAKA_POV = { lat: 14.6, lng: 76.2, altitude: 0.62 };

export default function GlobeMap({
  geo, choropleth = {}, maxFir = 1, selectedDistrict,
  zones = [], heatOn = true, hotspotsOn = true,
  predicted = null, predictedOn = false,
  patrol = null, patrolOn = true,
  flows = [], flowOn = true,
  onDistrict = () => {}, onHover = () => {},
}) {
  const containerRef = useRef(null);
  const worldRef = useRef(null);

  function colorFor(firs) {
    const t = Math.min(firs / maxFir, 1);
    if (t > 0.6) return `rgba(225,64,56,${(0.25 + t * 0.45).toFixed(2)})`;
    if (t > 0.3) return `rgba(255,176,32,${(0.18 + t * 0.4).toFixed(2)})`;
    return `rgba(34,230,240,${(0.10 + t * 0.3).toFixed(2)})`;
  }

  // mount once
  useEffect(() => {
    if (!containerRef.current || worldRef.current) return;
    let destroyed = false;
    import("globe.gl").then(({ default: Globe }) => {
      if (destroyed || !containerRef.current || worldRef.current) return;
      const el = containerRef.current;
      const world = Globe()(el)
        .width(el.offsetWidth)
        .height(el.offsetHeight)
        .backgroundColor("rgba(0,0,0,0)")
        .showAtmosphere(true)
        .atmosphereColor("#22E6F0")
        .atmosphereAltitude(0.13)
        .showGraticules(true)
        .polygonAltitude((f) => (f.properties?.NAME_2 === worldRef.current?.__sel ? 0.022 : f.__pred ? 0.012 : 0.008))
        .polygonSideColor(() => "rgba(34,230,240,.06)")
        .polygonsTransitionDuration(300)
        .onPolygonHover((f) => { el.style.cursor = f && !f.__pred ? "pointer" : ""; })
        .onPolygonClick((f) => {
          if (!f || f.__pred) return;
          const name = f.properties?.NAME_2;
          if (!name) return;
          // glide the camera to the district centroid
          const c = centroidOf(f);
          if (c) world.pointOfView({ lat: c.lat, lng: c.lng, altitude: 0.28 }, 700);
          onDistrict(name);
        })
        .pointLat("lat")
        .pointLng("lon")
        .hexBinPointLat("lat")
        .hexBinPointLng("lon")
        .pointAltitude((z) => 0.015 + Math.sqrt(Math.max(z.observed, 1)) * 0.004)
        .pointRadius((z) => 0.09 + Math.sqrt(Math.max(z.observed, 1)) * 0.05)
        .pointColor((z) => (z.is_hotspot ? "#ff4040" : "#7a8aa3"))
        .pointLabel((z) => `<div class="mx-hs">${z.zone} · ${z.observed} cases${z.is_hotspot ? " · confirmed hotspot" : ""}</div>`)
        .hexBinPointWeight("observed")
        .hexBinResolution(3)
        .hexAltitude((d) => 0.002 + Math.min(0.05, d.sumWeight * 0.0015))
        .hexTopColor(() => "rgba(34,230,240,.28)")
        .hexSideColor(() => "rgba(34,230,240,.10)")
        .arcColor(() => ["rgba(255,176,32,.85)", "rgba(255,140,66,.35)"])
        .arcAltitude(0.055)
        .arcStroke(0.42)
        .arcDashLength(0.45)
        .arcDashGap(0.25)
        .arcDashAnimateTime(1700)
        .arcLabel((a) => `<div class="mx-hs">${a.label}</div>`)
        .ringColor(() => (t) => `rgba(255,176,32,${1 - t})`)
        .ringMaxRadius(2.6)
        .ringPropagationSpeed(1.4)
        .ringRepeatPeriod(900);

      // dark navy sphere - no external texture, demo-safe offline
      const mat = world.globeMaterial();
      mat.color.set("#0a1322");
      mat.emissive?.set?.("#050a14");

      const controls = world.controls();
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.35;
      controls.enablePan = false;
      controls.minDistance = 120;
      const stopSpin = () => { controls.autoRotate = false; };
      el.addEventListener("pointerdown", stopSpin, { once: true });

      world.pointOfView(KARNATAKA_POV, 0);

      // live lat/lng readout under the pointer
      const onMove = (e) => {
        const r = el.getBoundingClientRect();
        const c = world.toGlobeCoords(e.clientX - r.left, e.clientY - r.top);
        onHover(c ? { lat: c.lat, lng: c.lng } : null);
      };
      el.addEventListener("pointermove", onMove);

      const onResize = () => world.width(el.offsetWidth).height(el.offsetHeight);
      window.addEventListener("resize", onResize);

      worldRef.current = world;
      world.__cleanup = () => {
        el.removeEventListener("pointermove", onMove);
        window.removeEventListener("resize", onResize);
      };
    });
    return () => {
      destroyed = true;
      try { worldRef.current?.__cleanup?.(); worldRef.current?._destructor?.(); } catch {}
      worldRef.current = null;
    };
  }, []); // eslint-disable-line

  function centroidOf(feature) {
    try {
      const ring = feature.geometry.type === "Polygon"
        ? feature.geometry.coordinates[0]
        : feature.geometry.coordinates.reduce((best, poly) => (poly[0].length > best[0].length ? poly : best))[0];
      let lat = 0, lng = 0;
      ring.forEach(([x, y]) => { lng += x; lat += y; });
      return { lat: lat / ring.length, lng: lng / ring.length };
    } catch { return null; }
  }

  // choropleth polygons (+ predicted contours when toggled)
  useEffect(() => {
    const world = worldRef.current;
    if (!world) return;
    const t = setInterval(() => { if (worldRef.current) { apply(); clearInterval(t); } }, 120);
    const apply = () => {
      const w = worldRef.current;
      if (!w) return;
      w.__sel = selectedDistrict || null;
      const base = geo?.features || [];
      const pred = predictedOn && predicted?.contours?.features
        ? predicted.contours.features.map((f) => ({ ...f, __pred: true }))
        : [];
      w.polygonsData([...base, ...pred])
        .polygonCapColor((f) => f.__pred
          ? (f.properties?.color || "#F97316") + "55"
          : colorFor(choropleth[f.properties?.NAME_2] || 0))
        .polygonStrokeColor((f) => f.__pred
          ? (f.properties?.color || "#F97316")
          : (f.properties?.NAME_2 === selectedDistrict ? "#22E6F0" : "rgba(34,230,240,.5)"))
        .polygonLabel((f) => f.__pred
          ? `<div class="mx-hs">predicted risk contour</div>`
          : `<div class="mx-hs">${f.properties?.NAME_2} · ${choropleth[f.properties?.NAME_2] || 0} FIRs</div>`);
    };
    apply();
    return () => clearInterval(t);
  }, [geo, choropleth, maxFir, selectedDistrict, predicted, predictedOn]); // eslint-disable-line

  // point + hex layers
  useEffect(() => {
    const world = worldRef.current;
    if (!world) return;
    world.pointsData(hotspotsOn ? zones : []);
    world.hexBinPointsData(heatOn ? zones : []);
  }, [zones, hotspotsOn, heatOn]);

  // crime-flow arcs
  useEffect(() => {
    worldRef.current?.arcsData(flowOn ? flows : []);
  }, [flows, flowOn]);

  // patrol pulse ring
  useEffect(() => {
    worldRef.current?.ringsData(patrolOn && patrol ? [patrol] : []);
  }, [patrol, patrolOn]);

  return <div ref={containerRef} className="mx-globe" />;
}
