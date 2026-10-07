
import re

with open("antar-frontend/components/AgentMascot.jsx", "r", encoding="utf-8") as f:
    code = f.read()

# Replace the AGENT_TYPES array to only the 7 core ones
agent_types = """const AGENT_TYPES = [
  { id: "network", name: "Network", color: "#00F5D4", icon: "M13 9a4 4 0 112 7l-4 4a4 4 0 11-6-6l2-2m13 0l2-2a4 4 0 00-6-6l-4 4a4 4 0 002 7" }, // Link
  { id: "pattern", name: "Pattern", color: "#60A5FA", icon: "M4 4h16v16H4V4zm4 4h8v8H8V8z" }, // Grid
  { id: "geo", name: "GeoSpatial", color: "#34EEB6", icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" }, // Pin
  { id: "forecast", name: "Forecast", color: "#E9D5FF", icon: "M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" }, // Chart
  { id: "linkage", name: "Linkage", color: "#6366F1", icon: "M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" }, // Puzzle
  { id: "brain", name: "Brain", color: "#EC4899", icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" }, // Brain
  { id: "research", name: "Research", color: "#34D399", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" }, // Document
];"""

code = re.sub(r"const AGENT_TYPES = \[.*?\];", agent_types, code, flags=re.DOTALL)

# Add onRun prop and onClick handler to the agent mascot
code = re.sub(r"export default function AgentMascot\(\) \{", "export default function AgentMascot({ onRun }) {", code)

# Look for <motion.div key={agent.id} drag
replacement = """<motion.div
            key={agent.id}
            drag
            onPointerDown={(e) => {
              // Only trigger run if it was a click, not a drag
              draggedRef.current.add(agent.id);
            }}
            onPointerUp={(e) => {
               if (draggedRef.current.has(agent.id)) {
                  draggedRef.current.delete(agent.id);
                  if (onRun) onRun();
               }
            }}
            dragMomentum={false}"""

# Actually, Framer Motion drag might conflict with onClick. Let's use onClick explicitly alongside drag!
replacement2 = """<motion.div
            key={agent.id}
            drag
            onClick={() => { if (onRun) onRun(); }}
            dragMomentum={false}"""

code = code.replace("<motion.div\n            key={agent.id}\n            drag\n            dragMomentum={false}", replacement2)

with open("antar-frontend/components/AgentMascot.jsx", "w", encoding="utf-8") as f:
    f.write(code)

