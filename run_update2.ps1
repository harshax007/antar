import re

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Rename px-stattile to px-statbox
content = content.replace('className="px-stattile"', 'className="px-statbox"')

# 2. Change Live badge to green
content = content.replace(
    '''<span className="pxd-sub" style={{ border: '1px solid rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>{dash && dash !== "offline" ? (kn ? "????" : "live") : "—"}</span>''',
    '''<span className="pxd-sub" style={{ border: '1px solid rgba(16,185,129,0.3)', background: 'rgba(16,185,129,0.1)', color: '#10b981', padding: '2px 6px', borderRadius: '4px', textTransform: 'uppercase' }}>{dash && dash !== "offline" ? (kn ? "????" : "live") : "—"}</span>'''
)

# 3. Add generateNarrative inside PredictScreen (before return)
narrative_code = """
  const generateNarrative = (item) => {
    if (!item) return "";
    const name = item.zone;
    const ctype = cap(item.crime_type);
    const z = item.z_score ? with an anomaly score of  : "";
    const rs = item.risk === "HIGH" ? "critical" : item.risk === "MEDIUM" ? "elevated" : "moderate";
    const dir = item.direction === "silence" ? "an unusual drop (possible under-reporting)" : "a predicted spike";
    if (kn) {
      return ???? AI ?????????:  ????????  ????????????  ??????????. ???  ????? ????????? ???????????.;
    }
    return Antar AI Analysis has identified a  risk of  for  in  . The underlying cause is linked to: .;
  };

  const avgConf = predictions?.length"""
content = content.replace('  const avgConf = predictions?.length', narrative_code)

# 4. Replace px-insp-why content
content = re.sub(
    r'<div className="px-insp-why">\{focusItem\.why \|\|[^\}]+\}</div>',
    '<div className="px-insp-why">{generateNarrative(focusItem)}</div>',
    content
)

# 5. Move px-statrow above px-dash
statrow_match = re.search(r'(\s*<div className="px-statrow">.*?</div\s*>\s*</div\s*>\s*</div\s*>\s*</div\s*>\s*</div\s*>)', content, re.DOTALL)
# Wait, parsing HTML with regex is fragile. 
# The px-statrow block is exactly:
#         <div className="px-statrow">
#           <div className="px-statbox">
#             <div className="l">{kn ? "???????????????" : "hotspots"}</div>
#             <div className="v">{predictions?.length ?? "—"}</div>
#           </div>
#           ...
#           <div className="px-statbox">
#             <div className="l">{kn ? "?????? ???????" : "avg confidence"}</div>
#             <div className="v cyan">{avgConf != null ? ${avgConf}% : "—"}</div>
#           </div>
#         </div>

with open('D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
