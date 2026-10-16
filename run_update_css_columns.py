import sys
import re

file_path = 'D:/Project/antar-frontend/app/globals.css'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace gd-blocks and gd-cols
search = """  .gd-blocks { display: grid; gap: 18px 28px; }
  .gd-cols { grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr)); }
  .gd-block { min-width: 0; }"""

replace = """  .gd-blocks { display: block; column-width: 260px; column-gap: 28px; }
  .gd-block { min-width: 0; break-inside: avoid; margin-bottom: 24px; display: inline-block; width: 100%; }"""

content = content.replace(search, replace)

# Also fix "Thought for ." which should be "Thought for ..."
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated CSS")