"use client";

import React, { useEffect, useRef } from "react";

export default function CinematicBackground() {
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.play().catch(() => {});
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 0,
        backgroundColor: "#070b0a",
      }}
    >
      {/* 1. Background Video Removed per request, keeping dark aesthetic */}
      {/* 2. Left-to-Right Dark Linear Gradient */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background: "linear-gradient(to right, #070b0a 0%, rgba(7,11,10,0.65) 45%, transparent 100%)",
        }}
      />

      {/* 3. Bottom-to-Top Dark Linear Gradient for Readability */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background: "linear-gradient(to top, #070b0a 0%, rgba(7,11,10,0.6) 35%, transparent 100%)",
        }}
      />

      {/* 4. Central Glow (Upper Center Horizontal Cyan-to-Dark-Green Ellipse with 25px Gaussian Blur) */}
      <div
        style={{
          position: "absolute",
          top: "12%",
          left: "50%",
          transform: "translateX(-50%)",
          width: "600px",
          height: "260px",
          borderRadius: "50%",
          background: "radial-gradient(ellipse at center, rgba(34,230,240,0.22) 0%, rgba(16,185,129,0.12) 50%, transparent 80%)",
          filter: "blur(25px)",
          opacity: 0.85,
        }}
      />
    </div>
  );
}
