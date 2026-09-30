import sys
filepath = r"D:\Project\antar-frontend\app\globals.css"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

if "details.ov-panel summary" not in content:
    content += "\ndetails.ov-panel summary { list-style: none; user-select: none; }\ndetails.ov-panel summary::-webkit-details-marker { display: none; }\n"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated globals.css for summary")
