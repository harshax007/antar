import sys

filepath = r"D:\Project\antar-frontend\components\BrainStructure.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Add focus overlay
overlay_code = """        {view === "net" && focus && <div className="bsx-focus-overlay" style={{position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', zIndex: 1, animation: 'fadeIn 0.3s ease', pointerEvents: 'none'}}></div>}
        {/* "?"? Focus panel"""

content = content.replace('{/* "?"? Focus panel', overlay_code)

# Hide calendar grid in focus mode
content = content.replace('!minActivity && (', '!minActivity && !focus && (')

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Added focus overlay and hidden calendar")
