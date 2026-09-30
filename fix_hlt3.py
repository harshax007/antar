import sys

filepath = r"D:\Project\antar-frontend\app\(app)\antar\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "const MessageRow = memo(({" in line:
        # We need to find the "}) => {" line below it
        for j in range(i, i+15):
            if "}) => {" in lines[j]:
                if "GLOBAL_HL_COUNT = 0;" not in lines[j+1]:
                    lines.insert(j+1, "    GLOBAL_HL_COUNT = 0;\n")
                break
        break

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Updated page.jsx with GLOBAL_HL_COUNT = 0;")
