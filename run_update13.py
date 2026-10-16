import sys
import re

file_path = 'D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Use narrative in UI
search_why_regex = r'<div className="px-insp-why">\{focusItem\.why.*?\}</div\s*>'
replace_why = '<div className="px-insp-why" style={{ background: "rgba(34,230,240,0.05)", padding: "16px 20px", borderRadius: "14px", borderLeft: "3px solid #22d3ee", color: "#e2e8f0", fontSize: "14.5px", lineHeight: "1.7", marginTop: "12px" }}>{generateNarrative(focusItem)}</div>'

content = re.sub(search_why_regex, replace_why, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")