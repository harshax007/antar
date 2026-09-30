import os
import sys

filepath = r"D:\Project\antar-frontend\.env.production"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the Catalyst URL with localhost
content = content.replace("NEXT_PUBLIC_API_URL=https://antar-api-50043861474.development.catalystappsail.in", "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated .env.production")
