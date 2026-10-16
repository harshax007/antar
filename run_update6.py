import sys

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('        {/* Hotspots KPI strip */}')
if start_idx != -1:
    end_idx = content.find('        {/* Explanation section', start_idx)
    if end_idx != -1:
        statrow_block = content[start_idx:end_idx]
        content = content[:start_idx] + content[end_idx:]
        
        insert_idx = content.find('        {/* Hero row: Predict next 7 days')
        if insert_idx != -1:
            content = content[:insert_idx] + statrow_block + content[insert_idx:]
        else:
            print("No insert target")
    else:
        print("No end")
else:
    print("No start")

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'w', encoding='utf-8') as f:
    f.write(content)