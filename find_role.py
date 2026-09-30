import sys

filepath = r"D:\Project\antar-frontend\app\(app)\antar\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "For your role" in line:
        print(f"Line {i}: {line.strip()}")
