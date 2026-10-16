import sys

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Change Live badge to green
search_live = '''<span className="pxd-sub" style={{ border: '1px solid rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>{dash && dash !== "offline" ? (kn ? "ಸಜೀವ" : "live") : "—"}</span>'''
replace_live = '''<span className="pxd-sub" style={{ border: '1px solid rgba(16,185,129,0.3)', background: 'rgba(16,185,129,0.1)', color: '#10b981', padding: '2px 6px', borderRadius: '4px', textTransform: 'uppercase' }}>{dash && dash !== "offline" ? (kn ? "ಸಜೀವ" : "live") : "—"}</span>'''
content = content.replace(search_live, replace_live)

# 2. Add generateNarrative
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

# 3. Use narrative in UI
search_why = '''<div className="px-insp-why">{focusItem.why || (kn ? "ಸ್ಥಳಾವಕಾಶದ ಹಾಟ್‌ಸ್ಪಾಟ್ ಅಸಂಗತತೆ ಕಂಡುಬಂದಿದೆ." : "Spatiotemporal hotspot anomaly detected.")}</div>'''
replace_why = '''<div className="px-insp-why" style={{ background: 'rgba(34,230,240,0.05)', padding: '12px 16px', borderRadius: '12px', borderLeft: '3px solid #22d3ee', color: '#cbd5e1' }}>{generateNarrative(focusItem)}</div>'''
content = content.replace(search_why, replace_why)

# 4. Move px-statrow above px-dash
# We will find the exact string of the statrow block.
import re
statrow_regex = r'(        {/\* Hotspots KPI strip \*/}\s*<div className="px-statrow">.*?</div\s*>\s*</div\s*>\s*</div\s*>\s*</div\s*>\s*</div\s*>)'
statrow_match = re.search(statrow_regex, content, re.DOTALL)
if statrow_match:
    statrow_block = statrow_match.group(1)
    content = content.replace(statrow_block, '')
    
    # insert before <div className="px-dash">
    insert_target = '        {/* Hero row: Predict next 7 days • Volume trend • Antar Alert */}'
    if insert_target in content:
        content = content.replace(insert_target, statrow_block + '\\n\\n' + insert_target)

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")