import sys
import re

filepath = r"D:\Project\antar-frontend\app\(app)\antar\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "{(showSuggestions?.length > 0 || roleSuggestions.length > 0) && (",
    "{!loading && (showSuggestions?.length > 0 || roleSuggestions.length > 0) && ("
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated page.jsx")
