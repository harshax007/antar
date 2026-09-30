"use client";

import { useState } from "react";
import useTypingPlaceholder from "@/lib/useTypingPlaceholder";

// A search input whose placeholder types out example queries.
//
// The animation state lives HERE, not in the parent: the placeholder changes ~14 times a
// second, and when that state sat in the Brain / Data Overview components every tick
// re-rendered the whole screen - restarting every chart's enter animation (the bars never
// finished growing) and re-rendering the 3D brain. Only this input re-renders now.
export default function TypingSearchInput({
  value, onChange, onKeyDown, examples = [], prefix = "", fallback = "", paused = false,
  className, ariaLabel, overridePlaceholder,
}) {
  const [focused, setFocused] = useState(false);
  const typed = useTypingPlaceholder(examples, { prefix, active: !focused && !value && !paused });
  return (
    <input
      className={className}
      aria-label={ariaLabel}
      placeholder={overridePlaceholder || typed || fallback}
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  );
}
