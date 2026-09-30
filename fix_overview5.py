import sys
filepath = r"D:\Project\antar-frontend\components\DataOverview.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# I will just revert DataOverview.jsx to how it was before I started, because parsing JSX with regex is failing constantly
content = content.replace("<details ", "<div ")
content = content.replace("</details>", "</div>")
content = content.replace("<summary ", "<div ")
content = content.replace("</summary>", "</div>")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Reverted DataOverview")
