import sys

filepath = r"D:\Project\antar-frontend\app\(app)\antar\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace Share2 icon with Network icon
content = content.replace('<Share2 size={14} />', '<Network size={14} />')

# Ensure Network is imported
if 'Share2,' in content:
    content = content.replace('Share2,', 'Network, Share2,')
elif '{ Share2' in content:
    content = content.replace('{ Share2', '{ Network, Share2')
else:
    # Let's just find the lucide-react import
    content = content.replace('from "lucide-react";', ', Network } from "lucide-react";')
    content = content.replace('}, Network }', '} }') # cleanup just in case
    content = content.replace(', Network, Network }', ', Network }')

# 2. Rename "For your role" to "Suggested"
role_target = """                      <span className="cx-sugg-lab cx-sugg-lab-role">
                        {kn ? (roleKey === "approver" ? "ಮೇಲ್ವಿಚಾರಣೆ" : "ನಿಮ್ಮ ಪಾತ್ರಕ್ಕಾಗಿ") : (roleKey === "approver" ? "For supervising" : "For your role")}
                      </span>"""
role_new = """                      <span className="cx-sugg-lab cx-sugg-lab-role">
                        {kn ? "ಸೂಚಿಸಲಾಗಿದೆ" : "Suggested"}
                      </span>"""
if role_target in content:
    content = content.replace(role_target, role_new)
else:
    print("Could not find 'For your role' span")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated antar/page.jsx")
