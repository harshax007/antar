import sys
import re

filepath = r"D:\Project\antar-frontend\app\(app)\antar\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(
    r'(translateAnswer,\s*rateAnswer,\s*toggleWhy\s*\})\s*=>\s*\{',
    r'\1 => {\n    GLOBAL_HL_COUNT = 0;',
    content,
    flags=re.DOTALL
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated page.jsx for GLOBAL_HL_COUNT reset")
