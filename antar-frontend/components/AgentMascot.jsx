
"use client";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

const AGENT_TYPES = [
  { id: "network", name: "Network", color: "#00F5D4", icon: "M13 9a4 4 0 112 7l-4 4a4 4 0 11-6-6l2-2m13 0l2-2a4 4 0 00-6-6l-4 4a4 4 0 002 7" }, // Link
  { id: "pattern", name: "Pattern", color: "#60A5FA", icon: "M4 4h16v16H4V4zm4 4h8v8H8V8z" }, // Grid
  { id: "geo", name: "GeoSpatial", color: "#34EEB6", icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" }, // Pin
  { id: "forecast", name: "Forecast", color: "#E9D5FF", icon: "M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" }, // Chart
  { id: "linkage", name: "Linkage", color: "#6366F1", icon: "M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" }, // Puzzle
  { id: "brain", name: "Brain", color: "#EC4899", icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" }, // Brain
  { id: "research", name: "Research", color: "#34D399", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" }, // Document
];

export default function AgentMascot({ onRun }) {
  const [agents, setAgents] = useState([]);
  const [formation, setFormation] = useState("patrol"); // patrol, assemble
  const [terminalAgent, setTerminalAgent] = useState(null);
  const [terminalInput, setTerminalInput] = useState("");
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
            onClick={() => setTerminalAgent(agent)}
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

      {/* Agent Terminal Window */}
      <AnimatePresence>
        {terminalAgent && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            style={{
              position: "fixed",
              bottom: "80px",
              right: "30px",
              width: "280px",
              background: "rgba(6, 11, 18, 0.95)",
              border: `1px solid ${terminalAgent.color}`,
              borderRadius: "6px",
              boxShadow: `0 8px 30px rgba(0,0,0,0.8), 0 0 15px ${terminalAgent.color}40`,
              zIndex: 10001,
              fontFamily: "JetBrains Mono, monospace",
              overflow: "hidden",
              backdropFilter: "blur(10px)",
              pointerEvents: "auto"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: `${terminalAgent.color}20`, padding: "6px 10px", borderBottom: `1px solid ${terminalAgent.color}40` }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={terminalAgent.color} strokeWidth="2"><path d={terminalAgent.icon} /></svg>
                <b style={{ color: terminalAgent.color, fontSize: "10px", letterSpacing: "0.05em" }}>BRAIN TERMINAL</b>
              </div>
              <button onClick={() => setTerminalAgent(null)} style={{ background: "none", border: "none", color: "#94A3B8", cursor: "pointer", fontSize: "14px", padding: 0 }}>&times;</button>
            </div>
            
            <div style={{ padding: "10px", height: "70px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px", color: "#E2E8F0", fontSize: "9px" }}>
              <div><span style={{color: "#94A3B8"}}>[SYS]</span> Secure link to <b style={{color: terminalAgent.color}}>${terminalAgent.name.toUpperCase()} AGENT</b> established. Awaiting instruction...</div>
              
              {terminalInput.trim().toLowerCase() === "run" && <div style={{ color: terminalAgent.color }}>${terminalAgent.name.toLowerCase()} &gt; Executing protocol...</div>}
            </div>

            <div style={{ padding: "6px 10px", borderTop: "1px solid rgba(255,255,255,0.1)", display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: terminalAgent.color, fontSize: "10px", fontWeight: "bold" }}>${terminalAgent.name.toLowerCase()} &gt;</span>
              <input 
                type="text" 
                autoFocus
                placeholder="run"
                value={terminalInput}
                onChange={(e) => setTerminalInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    if (terminalInput.trim().toLowerCase() === "run") {
                      if (onRun) onRun();
                      setTimeout(() => {
                        setTerminalAgent(null);
                        setTerminalInput("");
                      }, 1000);
                    } else {
                      setTerminalInput("");
                    }
                  }
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#FFF",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: "12px",
                  width: "100%",
                  outline: "none"
                }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}