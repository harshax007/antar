import sys

file_path = 'D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove uppercase
content = content.replace('text-transform: uppercase;', '/* text-transform: uppercase; */')

# 2. Darker background and borders
content = content.replace('background: #010409;', 'background: #000000;')
content = content.replace('background: #0d1117;', 'background: #050505;')
content = content.replace('rgba(22,27,34,0.8)', 'rgba(10,10,10,0.8)')
content = content.replace('rgba(13,17,23,0.9)', 'rgba(0,0,0,0.9)')
content = content.replace('border: 1px solid #30363d;', 'border: 1px solid #1a1a1a;')
content = content.replace('background: #161b22;', 'background: #080808;')
content = content.replace('border-bottom: 1px solid #21262d;', 'border-bottom: 1px solid #1a1a1a;')
content = content.replace('border: 1px solid #21262d;', 'border: 1px solid #1a1a1a;')
content = content.replace('border-color: #8b949e;', 'border-color: #333333;')
content = content.replace('background: #1c2128;', 'background: #0a0a0a;')
content = content.replace('border: 1px dashed #30363d;', 'border: 1px dashed #222222;')

# 3. Add details block for more information
search_prov = '''{focusItem.evidence_row_ids?.length > 0 && (
                      <div className="px-prov">
                        <div className="px-prov-hd"><span className="dot" />{kn ? "ಹೊಣೆಗಾರಿಕೆ ಲೆಡ್ಜರ್" : "Warning Ledger"} • {focusItem.evidence_row_ids.length} {kn ? "ಆದಾನ FIR ಸಾಲುಗಳು" : "input FIR rows persisted for audit"}</div>
                        <div className="px-prov-ids">
                          {focusItem.evidence_row_ids.slice(0, 4).join(" • ")}{focusItem.evidence_row_ids.length > 4 ? ` • +${focusItem.evidence_row_ids.length - 4}` : ""}
                        </div>
                      </div>
                    )}'''

# We need to make sure we replace the EXACT string, since there may be unicode mismatch in my python script string literal and the file.
# Let's use regex to find the px-prov block and wrap it.
import re
prov_regex = r'\{focusItem\.evidence_row_ids\?\.length > 0 && \(\s*<div className="px-prov">.*?</div\s*>\s*\)\}'
prov_match = re.search(prov_regex, content, re.DOTALL)

if prov_match:
    wrapped_prov = f"""{{focusItem.evidence_row_ids?.length > 0 && (
                      <details style={{ marginTop: '20px', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid #1a1a1a' }}>
                        <summary style={{ cursor: 'pointer', color: '#58a6ff', fontSize: '13px', fontWeight: 600, userSelect: 'none', display: 'flex', alignItems: 'center', outline: 'none' }}>
                          {{kn ? "ಹೆಚ್ಚಿನ ತಾಂತ್ರಿಕ ವಿವರಗಳನ್ನು ತೋರಿಸಿ (Show Details)" : "Show Deep Context & Evidence"}}
                        </summary>
                        <div style={{ marginTop: '16px' }}>
                          <div className="px-prov">
                            <div className="px-prov-hd"><span className="dot" />{{kn ? "ಹೊಣೆಗಾರಿಕೆ ಲೆಡ್ಜರ್" : "Warning Ledger"}} • {{focusItem.evidence_row_ids.length}} {{kn ? "ಆದಾನ FIR ಸಾಲುಗಳು" : "input FIR rows persisted for audit"}}</div>
                            <div className="px-prov-ids">
                              {{focusItem.evidence_row_ids.slice(0, 4).join(" • ")}}{{focusItem.evidence_row_ids.length > 4 ? ` • +${{focusItem.evidence_row_ids.length - 4}}` : ""}}
                            </div>
                          </div>
                          <div style={{ marginTop: '12px', fontSize: '12px', color: '#8b949e', fontFamily: 'JetBrains Mono' }}>
                            Model: Spatiotemporal MAD-z (Confidence {{focusItem.coverage || "90%"}})<br />
                            Z-score algorithm isolates true spikes from random statistical noise.<br />
                            {{focusItem.festival_driver ? `Holiday/Season Context: ${{focusItem.festival_driver}}` : ""}}
                          </div>
                        </div>
                      </details>
                    )}}"""
    content = content.replace(prov_match.group(0), wrapped_prov)
else:
    print("Could not find px-prov block")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")