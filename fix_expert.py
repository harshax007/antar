import sys
import re

filepath = r"D:\Project\antar-frontend\components\ExpertWorkspace.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Fix imports
content = content.replace('Activity, Square } from "lucide-react";', 'Activity, Square, Map, Cpu, Search } from "lucide-react";')

# 1. Remove Answer and Crosshair
callsign_old = """        <div className="c2-callsign">
          <Crosshair size={14} aria-hidden="true" />
          <b>{kn ? "ಉತ್ತರ" : "Answer"}</b><span>{kn ? "ತಜ್ಞ ಕಾರ್ಯಕ್ಷೇತ್ರ" : "Expert workspace"}</span>
        </div>"""
callsign_new = """        <div className="c2-callsign">
          <span>{kn ? "ತಜ್ಞ ಕಾರ್ಯಕ್ಷೇತ್ರ" : "Expert workspace"}</span>
        </div>"""
content = content.replace(callsign_old, callsign_new)

# 2. Add minimal Map, Brain, Search buttons
actions_old = """        <div className="c2-actions">
          <button onClick={exportReport} disabled={!sessionId} title="Export intelligence report"><Download size={13} /></button>"""
actions_new = """        <div className="c2-actions">
          <button title="Map"><Map size={13} /></button>
          <button title="Brain"><Cpu size={13} /></button>
          <button title="Search"><Search size={13} /></button>
          <button onClick={exportReport} disabled={!sessionId} title="Export intelligence report"><Download size={13} /></button>"""
content = content.replace(actions_old, actions_new)

# 3. Operations header
ops_old = """<b>{kn ? "ಕಾರ್ಯಾಚರಣೆಗಳು" : "Operations"}</b>"""
ops_new = """<b>{kn ? "ಕಾರ್ಯಾಚರಣೆಗಳು (ಎಕ್ಸ್‌ಪ್ಲೋರ್ ಮಾಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ)" : "Operations (click to explore)"}</b>"""
content = content.replace(ops_old, ops_new)

# 4. Remove repeated user question text from the top of the Brief tab
brief_old = """          {/* BRIEF */}
        {activeTab === "document" && (
            <div className="xw-doc">
              <div className="c2-label">{kn ? "ಪ್ರಶ್ನೆ" : "Question"}</div>
              <h1 className="xw-doctitle c2-title">{question || (kn ? "ಬುದ್ಧಿಮತ್ತೆ ಸಂಕ್ಷಿಪ್ತ" : "Intelligence brief")}</h1>"""
brief_new = """          {/* BRIEF */}
        {activeTab === "document" && (
            <div className="xw-doc">"""
content = content.replace(brief_old, brief_new)

# 5. Add "Suggested" tab to channels
channels_old = """  const channels = [
    ["document", kn ? "ಬ್ರೀಫ್" : "Brief", null],
    ["references", kn ? "ಸಾಕ್ಷ್ಯಗಳು" : "Evidence", citations?.length || 0],
    ["trace", kn ? "ಜಾಡು" : "Trace", trace?.length || 0],
    ["notes", kn ? "ಟಿಪ್ಪಣಿಗಳು" : "Notes", null]
  ];"""
channels_new = """  const channels = [
    ["document", kn ? "ಬ್ರೀಫ್" : "Brief", null],
    ["references", kn ? "ಸಾಕ್ಷ್ಯಗಳು" : "Evidence", citations?.length || 0],
    ["trace", kn ? "ಜಾಡು" : "Trace", trace?.length || 0],
    ["suggested", kn ? "ಸೂಚಿಸಲಾಗಿದೆ" : "Suggested", null],
    ["notes", kn ? "ಟಿಪ್ಪಣಿಗಳು" : "Notes", null]
  ];"""
content = content.replace(channels_old, channels_new)

# Insert Suggested tab content
tab_old = """        {/* LOG */}
        {activeTab === "notes" && ("""
tab_new = """        {/* SUGGESTED */}
        {activeTab === "suggested" && (
          <div className="xw-refs c2-list">
             <div className="xw-empty">{kn ? "ಸಂಬಂಧಿತ ಪ್ರಶ್ನೆಗಳು ಮತ್ತು ಸಂಪರ್ಕಗಳು ಇಲ್ಲಿವೆ." : "Related questions and connections will appear here."}</div>
          </div>
        )}
        
        {/* LOG */}
        {activeTab === "notes" && ("""
content = content.replace(tab_old, tab_new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated ExpertWorkspace.jsx")
