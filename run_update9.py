import sys
import re

file_path = 'D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Rename px-stattile to px-statbox
content = content.replace('className="px-stattile"', 'className="px-statbox"')

# 2. Change Live badge to green
search_live = '''<span className="pxd-sub" style={{ border: '1px solid rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>{dash && dash !== "offline" ? (kn ? "ಸಜೀವ" : "live") : "—"}</span>'''
replace_live = '''<span className="pxd-sub" style={{ border: '1px solid rgba(16,185,129,0.3)', background: 'rgba(16,185,129,0.1)', color: '#10b981', padding: '2px 8px', borderRadius: '6px', textTransform: 'uppercase' }}>{dash && dash !== "offline" ? (kn ? "ಸಜೀವ" : "live") : "—"}</span>'''
content = content.replace(search_live, replace_live)

# 3. Add generateNarrative
search_avg = '  const avgConf = predictions?.length'
replace_avg = """  const cap = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : "";
  const generateNarrative = (item) => {
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

# 4. Use narrative in UI
search_why = '''<div className="px-insp-why">{focusItem.why || (kn ? "ಸ್ಥಳಾವಕಾಶದ ಹಾಟ್‌ಸ್ಪಾಟ್ ಅಸಂಗತತೆ ಕಂಡುಬಂದಿದೆ." : "Spatiotemporal hotspot anomaly detected.")}</div>'''
replace_why = '''<div className="px-insp-why" style={{ background: 'rgba(34,230,240,0.05)', padding: '16px 20px', borderRadius: '14px', borderLeft: '3px solid #22d3ee', color: '#e2e8f0', fontSize: '14.5px', lineHeight: '1.7', marginTop: '12px' }}>{generateNarrative(focusItem)}</div>'''
content = content.replace(search_why, replace_why)

# 5. Move px-statrow above px-dash
start_tag = '      {/* Hotspots KPI strip */}'
end_tag = '      {/* Explanation section - full width'
start_idx = content.find(start_tag)
if start_idx != -1:
    end_idx = content.find(end_tag, start_idx)
    if end_idx != -1:
        statrow_block = content[start_idx:end_idx]
        content = content[:start_idx] + content[end_idx:]
        
        insert_target = '      {/* Hero row: Predict next 7 days'
        insert_idx = content.find(insert_target)
        if insert_idx != -1:
            content = content[:insert_idx] + statrow_block + '\\n' + content[insert_idx:]
        else:
            print("No insert target")
    else:
        print("No end tag")
else:
    print("No start tag")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")