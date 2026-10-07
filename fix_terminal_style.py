
import re

with open("antar-frontend/components/AgentMascot.jsx", "r", encoding="utf-8") as f:
    code = f.read()

# Replace the inner div of the terminal
replacement = """<div style={{ padding: "10px", height: "70px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px", color: "#E2E8F0", fontSize: "9px" }}>
              <div><span style={{color: "#94A3B8"}}>[SYS]</span> Secure link to <b style={{color: terminalAgent.color}}>${terminalAgent.name.toUpperCase()} AGENT</b> established. Awaiting instruction...</div>
              
              {terminalInput.trim().toLowerCase() === "run" && <div style={{ color: terminalAgent.color }}>${terminalAgent.name.toLowerCase()} &gt; Executing protocol...</div>}
            </div>

            <div style={{ padding: "6px 10px", borderTop: "1px solid rgba(255,255,255,0.1)", display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: terminalAgent.color, fontSize: "10px", fontWeight: "bold" }}>${terminalAgent.name.toLowerCase()} &gt;</span>
              <input 
                type="text" 
                autoFocus
                placeholder="run"
                value={terminalInput}"""

# Using regex to find the block to replace
code = re.sub(
    r"<div style={{ padding: \"10px\", height: \"70px\".*?value={terminalInput}",
    replacement,
    code,
    flags=re.DOTALL
)

with open("antar-frontend/components/AgentMascot.jsx", "w", encoding="utf-8") as f:
    f.write(code)

