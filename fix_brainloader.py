import sys
import re

filepath = r"D:\Project\antar-frontend\app\globals.css"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    ".brl-core { transform-origin: 0 0; animation: brlPulse 1.6s ease-in-out infinite; }",
    ".brl-core { transform-origin: 0 0; animation: brlPulse 1.6s cubic-bezier(0.65, 0.815, 0.735, 0.395) infinite; }"
)

if "animation: brlEnter 0.6s ease;" not in content:
    content = content.replace(
        ".brl { position: absolute;",
        "@keyframes brlEnter { from { opacity: 0; } to { opacity: 1; } }\n.brl { animation: brlEnter 0.6s ease; position: absolute;"
    )

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated globals.css for BrainLoader animation")
