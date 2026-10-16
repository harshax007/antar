import re

with open('D:/Project/antar-frontend/app/globals.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Define modern CSS overrides
replacements = [
    (r'\.pxd-card \{[^\}]+\}', '.pxd-card { display: flex; flex-direction: column; min-width: 0; min-height: 384px; max-height: 384px; border-radius: 20px; background: rgba(10, 15, 26, 0.45); backdrop-filter: blur(24px); border: 1px solid rgba(255, 255, 255, 0.05); box-shadow: 0 12px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05); padding: 20px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }'),
    
    (r'\.pxd-ttl \{[^\}]+\}', '.pxd-ttl { font-family: "Chakra Petch", sans-serif; font-size: 16px; font-weight: 700; color: #f8fafc; letter-spacing: 0.02em; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }'),
    
    (r'\.pxd-sub \{[^\}]+\}', '.pxd-sub { font-family: "JetBrains Mono", monospace; font-size: 11px; font-weight: 500; color: #64748b; white-space: nowrap; background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 12px; }'),
    
    (r'\.px-card \{[^\}]+\}', '.px-card { display: flex; flex-direction: column; width: 100%; text-align: left; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 14px; padding: 14px 16px; margin-bottom: 10px; cursor: pointer; color: var(--text); transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); gap: 8px; }'),
    
    (r'\.px-card:hover \{[^\}]+\}', '.px-card:hover { background: rgba(255, 255, 255, 0.04); border-color: rgba(255,255,255,0.1); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.25); }'),
    
    (r'\.px-card\.on \{[^\}]+\}', '.px-card.on { background: rgba(34, 230, 240, 0.06); border-color: rgba(34, 230, 240, 0.3); box-shadow: 0 4px 20px rgba(34,230,240,0.15), inset 0 0 0 1px rgba(34,230,240,0.1); }'),
    
    (r'\.px-card-top \{[^\}]+\}', '.px-card-top { display: flex; align-items: center; justify-content: space-between; gap: 9px; margin-bottom: 2px; }'),
    
    (r'\.px-zone \{[^\}]+\}', '.px-zone { font-family: "Inter", sans-serif; font-size: 14.5px; font-weight: 600; color: #f1f5f9; letter-spacing: -0.01em; }'),
    
    (r'\.px-risk \{[^\}]+\}', '.px-risk { font-family: "JetBrains Mono", monospace; font-size: 9.5px; font-weight: 700; letter-spacing: 0.06em; padding: 3px 8px; border-radius: 6px; text-transform: uppercase; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }'),
    
    (r'\.px-risk-h \{[^\}]+\}', '.px-risk-h { color: #f87171; background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.25); }'),
    
    (r'\.px-risk-m \{[^\}]+\}', '.px-risk-m { color: #fbbf24; background: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.25); }'),
    
    (r'\.px-risk-l \{[^\}]+\}', '.px-risk-l { color: #94a3b8; background: rgba(148, 163, 184, 0.12); border: 1px solid rgba(148, 163, 184, 0.25); }'),
    
    (r'\.px-crime-row \{[^\}]+\}', '.px-crime-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }'),
    
    (r'\.px-crime \{[^\}]+\}', '.px-crime { font-family: "Inter", sans-serif; font-size: 12.5px; font-weight: 500; color: #94a3b8; text-transform: capitalize; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }'),
    
    (r'\.px-know \{[^\}]+\}', '.px-know { flex: none; display: inline-flex; align-items: center; justify-content: center; font-family: "Inter", sans-serif; font-size: 11px; font-weight: 600; color: #38bdf8; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 6px 12px; cursor: pointer; white-space: nowrap; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }'),
    
    (r'\.px-know:hover \{[^\}]+\}', '.px-know:hover { background: rgba(56, 189, 248, 0.2); border-color: rgba(56, 189, 248, 0.4); color: #bae6fd; transform: scale(1.02); }'),

    (r'\.px-statbox \{[^\}]+\}', '.px-statbox { display: flex; flex-direction: column; background: rgba(10, 15, 26, 0.4); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 18px 22px; box-shadow: 0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.03); transition: transform 0.2s; }'),
    
    (r'\.px-statbox:hover \{[^\}]+\}', '.px-statbox:hover { transform: translateY(-2px); }'),
    
    (r'\.px-statbox \.l \{[^\}]+\}', '.px-statbox .l { font-family: "JetBrains Mono", monospace; font-size: 11px; font-weight: 600; color: #64748b; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 10px; }'),
    
    (r'\.px-statbox \.v \{[^\}]+\}', '.px-statbox .v { font-family: "Chakra Petch", sans-serif; font-size: 34px; font-weight: 800; color: #f8fafc; line-height: 1; letter-spacing: -0.02em; }'),

    (r'\.px-explain \{[^\}]+\}', '.px-explain { flex: 0 0 auto; display: flex; flex-direction: column; min-height: 0; background: rgba(8, 12, 20, 0.65); backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; overflow: hidden; box-shadow: 0 12px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05); }'),
    
    (r'\.px-explain-grid \{[^\}]+\}', '.px-explain-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px; }'),

    (r'\.px-bandbox \{[^\}]+\}', '.px-bandbox { font-size: 13px; font-family: "Inter", sans-serif; color: #e2e8f0; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px 16px; margin-bottom: 18px; box-shadow: inset 0 2px 10px rgba(0,0,0,0.1); }'),

    (r'\.px-tiles \{[^\}]+\}', '.px-tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px; }'),
    
    (r'\.px-tile \{[^\}]+\}', '.px-tile { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 14px; transition: background 0.2s; }'),
    
    (r'\.px-tile:hover \{[^\}]+\}', '.px-tile:hover { background: rgba(255,255,255,0.04); }'),
    
    (r'\.px-tile \.tv \{[^\}]+\}', '.px-tile .tv { font-family: "Chakra Petch", sans-serif; font-size: 17px; font-weight: 700; color: #f1f5f9; letter-spacing: 0.01em; }'),

    (r'\.px-actbtn \{[^\}]+\}', '.px-actbtn { font-family: "Inter", sans-serif; font-size: 12.5px; font-weight: 600; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 8px 16px; color: #cbd5e1; background: rgba(255,255,255,0.03); cursor: pointer; white-space: nowrap; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }'),
    
    (r'\.px-actbtn:hover \{[^\}]+\}', '.px-actbtn:hover { border-color: rgba(34,230,240,0.5); color: #fff; background: rgba(34,230,240,0.1); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(34,230,240,0.15); }'),
    
    (r'\.px-actbtn\.cy \{[^\}]+\}', '.px-actbtn.cy { color: #22d3ee; border-color: rgba(34,230,240,0.35); background: rgba(34,230,240,0.08); }'),

    (r'\.px-suggest \{[^\}]+\}', '.px-suggest { background: linear-gradient(135deg, rgba(34,230,240,0.08) 0%, rgba(16,185,129,0.08) 100%); border: 1px solid rgba(34,230,240,0.25); border-radius: 14px; padding: 18px 20px; margin-bottom: 20px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 4px 16px rgba(0,0,0,0.15); }'),
    
    (r'\.px-suggest-hd \{[^\}]+\}', '.px-suggest-hd { font-family: "JetBrains Mono", monospace; font-size: 11px; font-weight: 700; color: #22d3ee; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }'),
    (r'\.px-suggest-txt \{[^\}]+\}', '.px-suggest-txt { font-family: "Inter", sans-serif; font-size: 14px; color: #f8fafc; line-height: 1.6; }')
]

for pat, rep in replacements:
    css = re.sub(pat, rep, css)

with open('D:/Project/antar-frontend/app/globals.css', 'w', encoding='utf-8') as f:
    f.write(css)
