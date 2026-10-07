
import re

with open("antar-frontend/components/AgentMascot.jsx", "r", encoding="utf-8") as f:
    code = f.read()

# Replace the component logic
new_comp = """export default function AgentMascot() {
  const [agents, setAgents] = useState([]);
  const [formation, setFormation] = useState("patrol"); // patrol, assemble
  const draggedRef = useRef(new Set());

  useEffect(() => {
    // Initial spawn
    setAgents(AGENT_TYPES.map(a => ({
      ...a,
      x: window.innerWidth / 2 + (Math.random() * 400 - 200),
      y: window.innerHeight / 2 + (Math.random() * 300 - 150),
      status: "idle",
      log: "SYSTEM STANDBY"
    })));
  }, []);

  useEffect(() => {
    if (formation === "assemble") {
      // Line them up at the bottom of the screen
      const totalWidth = AGENT_TYPES.length * 60; // 42px width + gap
      const startX = (window.innerWidth - totalWidth) / 2;
      const targetY = window.innerHeight - 100;
      
      setAgents(prev => prev.map((a, i) => {
        if (draggedRef.current.has(a.id)) return a;
        return {
          ...a,
          status: "idle",
          log: "AWAITING ORDERS",
          x: startX + (i * 60),
          y: targetY
        };
      }));
      return; // Stop patrolling
    }

    // Patrol logic
    const interval = setInterval(() => {
      setAgents(prev => prev.map(a => {
        if (draggedRef.current.has(a.id)) return a;
        
        const isAnalyzing = Math.random() > 0.6;
        const targetX = Math.max(50, Math.min(window.innerWidth - 200, a.x + (Math.random() * 300 - 150)));
        const targetY = Math.max(50, Math.min(window.innerHeight - 150, a.y + (Math.random() * 200 - 100)));
        
        return {
          ...a,
          status: isAnalyzing ? "analyzing" : "moving",
          x: targetX,
          y: targetY,
          log: isAnalyzing ? `Analyzing ${a.name.toLowerCase()} telemetry...` : "Patrolling sector..."
        };
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, [formation]);

  return (
    <>
      {/* Assemble Control Button */}
      <div style={{ position: "fixed", bottom: "30px", right: "30px", zIndex: 10000 }}>
        <button 
          onClick={() => setFormation(f => f === "patrol" ? "assemble" : "patrol")}
          style={{
            background: "rgba(6, 11, 18, 0.8)",
            border: "1px solid #00F5D4",
            color: "#00F5D4",
            padding: "8px 16px",
            borderRadius: "4px",
            fontFamily: "Chakra Petch, sans-serif",
            textTransform: "uppercase",
            cursor: "pointer",
            boxShadow: "0 0 10px rgba(0,245,212,0.2)",
            backdropFilter: "blur(4px)"
          }}
          onMouseOver={(e) => e.currentTarget.style.background = "rgba(0, 245, 212, 0.2)"}
          onMouseOut={(e) => e.currentTarget.style.background = "rgba(6, 11, 18, 0.8)"}
        >
          {formation === "patrol" ? "Assemble Agents" : "Resume Patrol"}
        </button>
      </div>

      <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", pointerEvents: "none", zIndex: 9999 }}>
        {agents.map((agent) => (
          <motion.div
            key={agent.id}
            drag
            dragMomentum={false}
            onDragStart={() => draggedRef.current.add(agent.id)}
            onDragEnd={(e, info) => {
              draggedRef.current.delete(agent.id);
              setAgents(prev => prev.map(a => 
                a.id === agent.id ? { ...a, x: a.x + info.offset.x, y: a.y + info.offset.y, status: "analyzing", log: "Manual override engaged..." } : a
              ));
            }}
            animate={{ x: agent.x, y: agent.y }}
            transition={{ type: "spring", stiffness: 20, damping: 25 }}
            style={{
              position: "absolute",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              pointerEvents: "auto",
              cursor: "grab"
            }}
            whileDrag={{ scale: 1.1, cursor: "grabbing" }}
          >
            {/* Futuristic Agent Icon */}
            <motion.div
              animate={
                agent.status === "analyzing"
                  ? { rotate: [0, 90, 180, 270, 360], scale: [1, 1.15, 1] }
                  : { y: [0, -8, 0] }
              }
              transition={{
                repeat: Infinity,
                duration: agent.status === "analyzing" ? 3 : 5,
                ease: "linear"
              }}
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "50%",
                background: `rgba(6, 11, 18, 0.8)`,
                boxShadow: agent.status === "analyzing" 
                  ? `0 0 20px ${agent.color}, inset 0 0 10px ${agent.color}40` 
                  : `0 0 10px ${agent.color}40`,
                border: `1.5px solid ${agent.color}`,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                backdropFilter: "blur(4px)"
              }}
            >
              <motion.svg 
                animate={{ rotate: agent.status === "analyzing" ? -360 : 0 }} 
                transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
                width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={agent.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              >
                <path d={agent.icon} />
              </motion.svg>
            </motion.div>

            {/* Holographic Label */}
            <AnimatePresence>
              {(agent.status === "analyzing" || formation === "assemble") && (
                <motion.div
                  initial={{ opacity: 0, x: -10, scale: 0.9 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  style={{
                    background: "linear-gradient(90deg, rgba(6,11,18,0.9) 0%, rgba(6,11,18,0.4) 100%)",
                    borderLeft: `2px solid ${agent.color}`,
                    padding: "6px 12px",
                    borderRadius: "0 4px 4px 0",
                    display: formation === "assemble" ? "none" : "flex", // Hide huge logs when assembled so they fit
                    flexDirection: "column",
                    gap: "2px"
                  }}
                >
                  <b style={{ color: agent.color, fontSize: "11px", fontFamily: "Chakra Petch, sans-serif", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    {agent.name} AGENT
                  </b>
                  <span style={{ color: "#94A3B8", fontSize: "9px", fontFamily: "JetBrains Mono, monospace" }}>
                    {agent.log}
                  </span>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
    </>
  );
}"""

code = re.sub(r"export default function AgentMascot\(\) \{.*$", new_comp, code, flags=re.DOTALL)

with open("antar-frontend/components/AgentMascot.jsx", "w", encoding="utf-8") as f:
    f.write(code)

