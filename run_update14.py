import sys

file_path = 'D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\\n      {/* Hero row: Predict next 7 days', '      {/* Hero row: Predict next 7 days')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Removed \n")