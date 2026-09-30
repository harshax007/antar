import sys
import re

filepath = r"D:\Project\antar-frontend\components\DataOverview.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace <div className="ov-panel ov-clock"> with <details className="ov-panel ov-clock">
content = content.replace(
    '<div className="ov-panel ov-clock">',
    '<details className="ov-panel ov-clock">'
)

content = content.replace(
    '<div className="ov-panel ov-outcomes">',
    '<details className="ov-panel ov-outcomes">'
)

# Convert the title divs to summaries
content = re.sub(
    r'<div className="ov-ptitle">([\s\S]*?)</div>\n\s*<div className="ov-clock-head">',
    r'<summary className="ov-ptitle" style={{cursor: "pointer"}}> \1 </summary>\n          <div className="ov-clock-head">',
    content
)

content = re.sub(
    r'<div className="ov-ptitle">([\s\S]*?)</div>\n\s*<div className="ov-out-circles">',
    r'<summary className="ov-ptitle" style={{cursor: "pointer"}}> \1 </summary>\n          <div className="ov-out-circles">',
    content
)

# Now for the closing </div> of ov-panel...
# Since this is a bit tricky, let's just replace the closing divs for these specific panels
content = content.replace(
    '          </div>\n        </div>\n        <div className="ov-panel ov-outcomes">',
    '          </div>\n        </details>\n        <details className="ov-panel ov-outcomes">'
)

content = content.replace(
    '          </div>\n        </div>\n      </div>\n    );\n  }',
    '          </div>\n        </details>\n      </div>\n    );\n  }'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated DataOverview.jsx")
