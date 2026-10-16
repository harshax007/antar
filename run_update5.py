import sys
import re

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('className="px-stattile"', 'className="px-statbox"')

content = re.sub(
    r'<span className="pxd-sub" style=\{\{\s*border:\s*\'1px solid rgba\(255,255,255,0\.1\)\',\s*padding:\s*\'2px 6px\',\s*borderRadius:\s*\'4px\'\s*\}\}>(\{dash)',
    r'<span className="pxd-sub" style={{ border: \"1px solid rgba(16,185,129,0.3)\", background: \"rgba(16,185,129,0.1)\", color: \"#10b981\", padding: \"2px 8px\", borderRadius: \"6px\", textTransform: \"uppercase\" }}>\g<1>',
    content
)

search_avg = '  const avgConf = predictions?.length'
replace_avg = """  const generateNarrative = (item) => {
    if (!item) return "";
    const name = item.zone;
    const ctype = cap(item.crime_type);
    const z = item.z_score ? with an anomaly score of  : "";
    const rs = item.risk === "HIGH" ? "critical" : item.risk === "MEDIUM" ? "elevated" : "moderate";
    const dir = item.direction === "silence" ? "an unusual drop (possible under-reporting)" : "a predicted spike";
    if (kn) {
      return ಅಂತರ AI ವಿಶ್ಲೇಷಣೆ:  ವಲಯದಲ್ಲಿ  ಪ್ರಕರಣಗಳಲ್ಲಿ  ಕಂಡುಬಂದಿದೆ. ಇದು  ಮಟ್ಟದ ಅಪಾಯವನ್ನು ಸೂಚಿಸುತ್ತದೆ.;
    }
    return Antar AI Analysis has identified a  risk of  for  in  . The underlying cause is linked to: .;
  };

  const avgConf = predictions?.length"""
content = content.replace(search_avg, replace_avg)

content = re.sub(
    r'<div className="px-insp-why">\{focusItem\.why.*?</div\s*>',
    r'<div className="px-insp-why" style={{ background: "rgba(34,230,240,0.05)", padding: "16px 20px", borderRadius: "14px", borderLeft: "3px solid #22d3ee", color: "#e2e8f0" }}>{generateNarrative(focusItem)}</div>',
    content
)

statrow_regex = r'(\s*\{\/\*\s*Hotspots KPI strip\s*\*\/\}\s*<div className="px-statrow">.*?</div\s*>\s*</div\s*>\s*</div\s*>\s*</div\s*>\s*</div\s*>)'
statrow_match = re.search(statrow_regex, content, re.DOTALL)
if statrow_match:
    statrow_block = statrow_match.group(1)
    content = content.replace(statrow_block, '')
    
    insert_target = '        {/* Hero row: Predict next 7 days'
    if insert_target in content:
        content = content.replace(insert_target, statrow_block.strip() + '\\n\\n' + insert_target)
    else:
        print("Could not find insert target")
else:
    print("Could not find statrow block")

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")