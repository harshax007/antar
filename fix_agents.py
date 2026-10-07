
import re

agent_types = """const AGENT_TYPES = [
  { id: "query", name: "Query", color: "#3B82F6", icon: "M4 7v10c0 2 1.5 3 4 3h8c2.5 0 4-1 4-3V7M4 7c0-2 1.5-3 4-3h8c2.5 0 4 1 4 3M4 7c0 2 1.5 3 4 3h8c2.5 0 4-1 4-3" }, // Database
  { id: "network", name: "Network", color: "#00F5D4", icon: "M13 9a4 4 0 112 7l-4 4a4 4 0 11-6-6l2-2m13 0l2-2a4 4 0 00-6-6l-4 4a4 4 0 002 7" }, // Link
  { id: "profile", name: "Profiler", color: "#FFB020", icon: "M12 14a7 7 0 00-7 7h14a7 7 0 00-7-7zM16 7a4 4 0 11-8 0 4 4 0 018 0z" }, // User
  { id: "forecast", name: "Forecast", color: "#E9D5FF", icon: "M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" }, // Chart
  { id: "social", name: "Social", color: "#F472B6", icon: "M17 20h5V10l-10-8L2 10v10h5" }, // People (house proxy) -> Let's use users: "M12 4a4 4 0 100 8 4 4 0 000-8zM2 20h20M12 14c-4 0-7 2-7 6"
  { id: "geo", name: "GeoSpatial", color: "#34EEB6", icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" }, // Pin
  { id: "predict", name: "Predict", color: "#FBBF24", icon: "M13 10V3L4 14h7v7l9-11h-7z" }, // Lightning
  { id: "pattern", name: "Pattern", color: "#60A5FA", icon: "M4 4h16v16H4V4zm4 4h8v8H8V8z" }, // Grid
  { id: "alert_suggest", name: "Alerts", color: "#EF4444", icon: "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" }, // Bell
  { id: "osint", name: "OSINT", color: "#A78BFA", icon: "M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" }, // Globe
  { id: "research", name: "Research", color: "#34D399", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" }, // Clipboard
  { id: "brain", name: "Brain", color: "#EC4899", icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" }, // Bulb/Brain
  { id: "advocate", name: "Advocate", color: "#F87171", icon: "M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" }, // Lock/Shield
  { id: "vigil", name: "Vigil", color: "#10B981", icon: "M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" }, // Eye
  { id: "linkage", name: "Linkage", color: "#6366F1", icon: "M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" }, // Squares overlapping
  { id: "sentinel", name: "Sentinel", color: "#F59E0B", icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" } // Shield check
];"""

with open("antar-frontend/components/AgentMascot.jsx", "r", encoding="utf-8") as f:
    code = f.read()

code = re.sub(r"const AGENT_TYPES = \[.*?\];", agent_types, code, flags=re.DOTALL)
with open("antar-frontend/components/AgentMascot.jsx", "w", encoding="utf-8") as f:
    f.write(code)

