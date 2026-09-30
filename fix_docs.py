import sys

filepath = r"D:\Project\antar-frontend\app\(app)\docs\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

target = """        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "10px" }}>
          {status === "running" ? (
            <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: statusColor, boxShadow: `0 0 10px ${statusColor}` }} />
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "9.5px", color: "#64748B", letterSpacing: "0.05em", textTransform: "capitalize" }}>{actionVerb}...</span>
            </motion.div>
          ) : (
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "11px", color: status === "done" ? "#FFFFFF" : statusColor, fontWeight: 500, letterSpacing: "0.02em" }}>{statusLabel}</span>
          )}"""

replacement = """        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "10px", minWidth: "120px", justifyContent: "flex-end" }}>
          <motion.div 
            animate={{ opacity: status === "running" ? [0.4, 1, 0.4] : 1 }} 
            transition={{ repeat: status === "running" ? Infinity : 0, duration: 1.5 }} 
            style={{ display: "flex", alignItems: "center", gap: "8px" }}
          >
            <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: statusColor, boxShadow: `0 0 10px ${statusColor}` }} />
            <span style={{ 
              fontFamily: "'Inter', sans-serif", 
              fontSize: "11px", 
              color: status === "done" ? "#FFFFFF" : (status === "running" ? "#64748B" : statusColor), 
              fontWeight: 500, 
              letterSpacing: "0.02em", 
              textTransform: status === "running" ? "capitalize" : "none",
              width: "100px",
              textAlign: "left"
            }}>
              {status === "running" ? `${actionVerb}...` : statusLabel}
            </span>
          </motion.div>"""

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated docs/page.jsx")
else:
    print("Could not find target in docs/page.jsx")
