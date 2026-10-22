"use client";

// A window that arrives the way Apple's sheets do: it grows out of the point the officer
// pressed to open it and goes back into that same point when closed (spatial consistency),
// it materialises - scale and blur together - rather than only fading, and it is a spring,
// so a close pressed half-way through the opening turns it round from where it is
// (interruptible) instead of finishing the opening first.
//
//   <AnimatePresence>
//     {open && (
//       <MaterialBackdrop key="x" className="my-overlay" onClick={close}>
//         <MaterialPanel as="section" className="my-window">…</MaterialPanel>
//       </MaterialBackdrop>
//     )}
//   </AnimatePresence>
//
// Reduced motion: a short cross-fade only, no scale or blur.

import { forwardRef, useLayoutEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";

// Where the last press landed - the trigger of whatever opens next. Read at mount.
let lastPress = null;
if (typeof window !== "undefined") {
  window.addEventListener("pointerdown", (e) => { lastPress = { x: e.clientX, y: e.clientY, t: Date.now() }; }, true);
}

// Critically damped (Apple's default for UI that was not flicked): no overshoot.
export const SPRING = { type: "spring", bounce: 0, duration: 0.38 };
const FADE = { duration: 0.16, ease: "easeOut" };

export function MaterialBackdrop({ children, className, onClick, ...rest }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} onClick={onClick}
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      transition={reduce ? FADE : { duration: 0.22, ease: "easeOut" }}
      style={{ animation: "none" }} {...rest}>
      {children}
    </motion.div>
  );
}

export const MaterialPanel = forwardRef(function MaterialPanel({ as = "div", children, style, ...rest }, outerRef) {
  const reduce = useReducedMotion();
  const ref = useRef(null);
  const Tag = motion[as] || motion.div;

  // Grow from the press point, expressed in the panel's own box. Some windows open a moment
  // after the press (Fast Run counts first); a press older than 4 s is not what opened this
  // one (keyboard, or opened by code), so it grows from the centre.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const p = lastPress && Date.now() - lastPress.t < 4000 ? lastPress : null;
    // The box is measured already scaled to 0.92 about its centre; undo that so the
    // origin lands on the press point in the full-size window.
    const w = el.offsetWidth, h = el.offsetHeight;
    const left = r.left - (w - r.width) / 2, top = r.top - (h - r.height) / 2;
    if (p && w && h) {
      const x = Math.max(0, Math.min(w, p.x - left));
      const y = Math.max(0, Math.min(h, p.y - top));
      el.style.transformOrigin = `${x}px ${y}px`;
    }
  }, []);

  const setRefs = (el) => {
    ref.current = el;
    if (typeof outerRef === "function") outerRef(el);
    else if (outerRef) outerRef.current = el;
  };

  const hidden = reduce ? { opacity: 0 } : { opacity: 0, scale: 0.92, filter: "blur(6px)" };
  const shown = reduce ? { opacity: 1 } : { opacity: 1, scale: 1, filter: "blur(0px)" };
  return (
    <Tag ref={setRefs} initial={hidden} animate={shown} exit={hidden}
      transition={reduce ? FADE : SPRING}
      style={{ willChange: "transform, opacity, filter", animation: "none", ...style }} {...rest}>
      {children}
    </Tag>
  );
});

export default MaterialPanel;
