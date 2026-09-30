import sys

filepath = r"D:\Project\antar-frontend\app\globals.css"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

import re

# Replace cx-line
content = re.sub(
    r'\.cx-line \{[^}]*\}',
    r'.cx-line { padding: 3px 0 3px 14px; line-height: 1.62; color: #D1D5DB; display: flex; align-items: flex-start; }',
    content
)

content = re.sub(
    r'\.cx-linenum \{[^}]*\}',
    r'.cx-linenum { color: var(--cyan); font-weight: 700; margin-right: 8px; font-family: \'Chakra Petch\'; min-width: 20px; text-align: right; flex-shrink: 0; }',
    content
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated globals.css")
