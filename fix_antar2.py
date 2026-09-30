import sys

filepath = r"D:\Project\antar-frontend\app\(app)\antar\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

import re
# We just replace the entire span content based on "For your role"
content = re.sub(
    r'<span className="cx-sugg-lab cx-sugg-lab-role">\s*\{kn \?.*?For your role"\)\}\s*</span>',
    r'<span className="cx-sugg-lab cx-sugg-lab-role">\n                        {kn ? "ಸೂಚಿಸಲಾಗಿದೆ" : "Suggested"}\n                      </span>',
    content,
    flags=re.DOTALL
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated antar/page.jsx successfully")
