import sys
file_path = 'D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("<details style={ marginTop:", "<details style={{ marginTop:")
content = content.replace("border: '1px solid #1a1a1a' }>", "border: '1px solid #1a1a1a' }}>")

content = content.replace("<summary style={ cursor:", "<summary style={{ cursor:")
content = content.replace("outline: 'none' }>", "outline: 'none' }}>")

content = content.replace("<div style={ marginTop: '16px' }>", "<div style={{ marginTop: '16px' }}>")
content = content.replace("<div style={ marginTop: '12px'", "<div style={{ marginTop: '12px'")
content = content.replace("fontFamily: 'JetBrains Mono' }>", "fontFamily: 'JetBrains Mono' }}>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed JSX syntax")