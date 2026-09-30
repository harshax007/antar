"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { asset } from "@/lib/assets";

const ALLOWED_3D_SCREENS = ["/antar", "/antarBrain", "/map", "/predict", "/search"];

export default function ScreenTransition3D({ targetPath, lang = "en" }) {
  const shouldShow =
    targetPath &&
    ALLOWED_3D_SCREENS.some((k) => targetPath === k || targetPath.startsWith(`${k}/`) || targetPath === `${k}`);

  if (!shouldShow) return null;

  return (
    <AnimatePresence>
      {targetPath && (
        <motion.div
          key="transition-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18, ease: "easeInOut" }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(5, 8, 16, 0.45)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
            overflow: "hidden",
            pointerEvents: "none",
          }}
        >
          {/* Central Video Container */}
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 1.05, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            style={{
              width: "180px", 
              height: "180px",
              borderRadius: "50%",
              overflow: "hidden",
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 40px rgba(34, 230, 240, 0.3), inset 0 0 20px rgba(34, 230, 240, 0.2)",
              border: "1px solid rgba(34, 230, 240, 0.4)",
              background: "#000"
            }}
          >
            <video 
              src={asset("/brand/video/loading.mp4")}
              autoPlay
              loop
              muted
              playsInline
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          </motion.div>
          
          {/* Outer Ring for extra polish */}
          <motion.div
            animate={{ rotateZ: 360 }}
            transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
            style={{
              position: "absolute",
              width: "210px",
              height: "210px",
              borderRadius: "50%",
              border: "1px dashed rgba(34, 230, 240, 0.4)",
              pointerEvents: "none"
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
