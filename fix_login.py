import sys

filepath = r'D:\Project\antar-frontend\app\(auth)\login\page.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace cyan loading line with gray line
content = content.replace('background: "#22e6f0"', 'background: "#94A3B8"')
content = content.replace('boxShadow: "0 0 8px #22e6f0"', 'boxShadow: "0 0 8px #94A3B8"')

# Remove "Establishing Secure Connection..." block
start_idx = content.find('<div style={{ color: "#22e6f0"')
if start_idx != -1:
    end_idx = content.find('</div>', start_idx) + 6
    content = content[:start_idx] + content[end_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated login page")
