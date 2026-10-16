import re

file_path = 'D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the PREDICT_MODERN_STYLES completely
new_styles = """const PREDICT_MODERN_STYLES = `
/* Antar Tactical UI - High Contrast, Data-Dense */
.px-page { background: #010409; color: #e6edf3; font-family: 'Inter', sans-serif; }

/* Typography */
.px-title { color: #58a6ff; font-family: 'Chakra Petch', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: 0.03em; text-shadow: 0 0 15px rgba(88,166,255,0.4); margin-bottom: 4px; }
.px-sub { font-size: 13px; color: #8b949e; font-weight: 500; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.05em; }

/* Buttons */
.px-howbtn { background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.3); color: #58a6ff; border-radius: 6px; font-weight: 600; font-size: 12px; padding: 6px 12px; transition: all 0.2s; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.px-howbtn:hover { background: rgba(88,166,255,0.2); box-shadow: 0 0 10px rgba(88,166,255,0.2); }

/* Grid Layouts */
.px-dash { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding-bottom: 24px; }

/* Top KPI Strip */
.px-statrow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-top: 16px; margin-bottom: 32px; }
.px-statbox { position: relative; display: flex; flex-direction: column; background: linear-gradient(180deg, rgba(22,27,34,0.8) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid #30363d; border-radius: 12px; padding: 20px 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); overflow: hidden; }
.px-statbox::before { content: ""; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: #30363d; }
.px-statbox:hover { border-color: #58a6ff; }
.px-statbox:hover::before { background: #58a6ff; box-shadow: 0 0 8px #58a6ff; }
.px-statbox .l { font-size: 11px; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; }
.px-statbox .v { font-size: 38px; font-weight: 800; color: #c9d1d9; font-family: 'Chakra Petch', sans-serif; line-height: 1; }
.px-statbox .v.cyan { color: #58a6ff; }
.px-statbox .v.red { color: #ff7b72; }

/* Columns */
.pxd-card { display: flex; flex-direction: column; min-height: 440px; max-height: 480px; border-radius: 12px; background: #0d1117; border: 1px solid #30363d; box-shadow: 0 12px 32px rgba(0,0,0,0.4); padding: 20px; }
.pxd-hd { margin-bottom: 20px; border-bottom: 1px solid #21262d; padding-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.pxd-ttl { font-family: 'Chakra Petch', sans-serif; font-size: 16px; font-weight: 700; color: #e6edf3; letter-spacing: 0.05em; text-transform: uppercase; }

/* Scroll Area */
.pxd-scroll { flex: 1; overflow-y: auto; padding-right: 8px; }
.pxd-scroll::-webkit-scrollbar { width: 6px; }
.pxd-scroll::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
.pxd-scroll::-webkit-scrollbar-track { background: transparent; }

/* Cards inside columns */
.px-card { display: flex; flex-direction: column; background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; margin-bottom: 12px; cursor: pointer; transition: all 0.2s; position: relative; }
.px-card:hover { border-color: #8b949e; background: #1c2128; }
.px-card.on { background: rgba(88,166,255,0.08); border-color: #58a6ff; box-shadow: 0 0 15px rgba(88,166,255,0.15); }
.px-card.on::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: #58a6ff; border-radius: 4px 0 0 4px; }

.px-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.px-zone { font-size: 15px; font-weight: 700; color: #c9d1d9; letter-spacing: 0.02em; }

/* Risk Tags */
.px-risk { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 800; padding: 4px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.1em; }
.px-risk-h { color: #ff7b72; background: rgba(255,123,114,0.15); border: 1px solid rgba(255,123,114,0.3); }
.px-risk-m { color: #d2a8ff; background: rgba(210,168,255,0.15); border: 1px solid rgba(210,168,255,0.3); }
.px-risk-l { color: #8b949e; background: rgba(139,148,158,0.15); border: 1px solid rgba(139,148,158,0.3); }

/* Data Rows */
.px-crime-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.px-crime { font-size: 13px; color: #8b949e; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.px-know { font-size: 11px; font-weight: 600; padding: 6px 12px; background: rgba(46,160,67,0.1); border: 1px solid rgba(46,160,67,0.4); border-radius: 6px; color: #3fb950; transition: all 0.2s; white-space: nowrap; cursor: pointer; }
.px-know:hover { background: rgba(46,160,67,0.2); box-shadow: 0 0 8px rgba(46,160,67,0.3); }

.px-confpct { color: #58a6ff; font-weight: 700; font-size: 13px; font-family: 'JetBrains Mono', monospace; }
.px-meta { margin-top: 12px; font-size: 11px; color: #8b949e; display: flex; gap: 8px; flex-wrap: wrap; }
.px-tag { font-size: 10px; padding: 4px 8px; border-radius: 4px; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; font-family: 'JetBrains Mono', monospace; }
.px-tag.ok { color: #58a6ff; border-color: rgba(88,166,255,0.4); background: rgba(88,166,255,0.1); }

/* Explanation Panel */
.px-explain { background: #0d1117; border: 1px solid #30363d; border-radius: 12px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); overflow: hidden; margin-top: 24px; }
.px-panel-hd { background: #161b22; padding: 16px 24px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 700; color: #c9d1d9; font-family: 'Chakra Petch', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; }
.px-hint { font-size: 12px; font-weight: 500; color: #8b949e; font-family: 'JetBrains Mono', monospace; }
.px-insp { padding: 32px; }
.px-insp-title { font-family: 'Chakra Petch', sans-serif; font-size: 28px; font-weight: 700; color: #e6edf3; margin-bottom: 16px; letter-spacing: 0.02em; }

/* AI Explanation Box */
.px-insp-why { background: rgba(88,166,255,0.05); padding: 20px 24px; border-radius: 8px; border-left: 4px solid #58a6ff; color: #c9d1d9; font-size: 15px; line-height: 1.6; margin-bottom: 28px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-weight: 500; }

/* Stats in explanation */
.px-big .n { font-size: 48px; font-weight: 800; color: #e6edf3; font-family: 'Chakra Petch', sans-serif; }
.px-big .z { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: #ff7b72; background: rgba(255,123,114,0.1); border: 1px solid rgba(255,123,114,0.3); padding: 6px 12px; border-radius: 6px; margin-left: 16px; vertical-align: super; }

/* Band box */
.px-bandbox { font-family: 'JetBrains Mono', monospace; font-size: 13px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; color: #8b949e; }
.px-bandbox b { color: #58a6ff; font-size: 15px; font-weight: 700; margin-right: 8px; }

/* Grid tiles */
.px-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
.px-tile { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; transition: all 0.2s; }
.px-tile:hover { border-color: #58a6ff; box-shadow: 0 4px 12px rgba(88,166,255,0.1); }
.px-tile .tv { font-family: 'Chakra Petch', sans-serif; font-size: 24px; font-weight: 700; color: #e6edf3; margin-bottom: 6px; }
.px-tile .tl { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; }

/* Actions */
.px-acts { display: flex; flex-wrap: wrap; gap: 12px; }
.px-actbtn { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; padding: 10px 20px; border-radius: 6px; border: 1px solid #30363d; background: #21262d; color: #c9d1d9; transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; min-width: 140px; }
.px-actbtn:hover { background: #30363d; border-color: #8b949e; color: #fff; }
.px-actbtn.cy { background: rgba(46,160,67,0.1); border-color: rgba(46,160,67,0.4); color: #3fb950; }
.px-actbtn.cy:hover { background: rgba(46,160,67,0.2); box-shadow: 0 0 12px rgba(46,160,67,0.2); }

/* Suggestion */
.px-suggest { background: linear-gradient(135deg, rgba(88,166,255,0.05) 0%, rgba(46,160,67,0.05) 100%); border: 1px solid rgba(88,166,255,0.2); border-radius: 12px; padding: 24px; margin-bottom: 32px; border-left: 4px solid #58a6ff; }
.px-suggest-hd { font-family: "JetBrains Mono", monospace; font-size: 12px; font-weight: 700; color: #58a6ff; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.px-suggest-txt { font-size: 15px; color: #e6edf3; line-height: 1.6; font-weight: 500; }

.px-prov-hd { font-size: 12px; font-weight: 600; color: #8b949e; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
.px-prov-ids { font-family: "JetBrains Mono", monospace; font-size: 11px; color: #8b949e; background: #010409; padding: 12px; border-radius: 6px; border: 1px dashed #30363d; }
`;"""

content = re.sub(r'const PREDICT_MODERN_STYLES = `.*?`;', new_styles, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")