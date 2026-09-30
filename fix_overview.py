import sys
import re

filepath = r"D:\Project\antar-frontend\components\DataOverview.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace <div className="ov-panel ov-clock"> with <details className="ov-panel ov-clock"><summary>
# and <div className="ov-clock-head"> ... </div> with </summary> <div className="ov-clock-body">
content = content.replace(
    '<div className="ov-panel ov-clock">',
    '<details className="ov-panel ov-clock">'
)

content = content.replace(
    '<div className="ov-ptitle">\n            {kn ? "à²šà²¾à²°à³à²œà³â€Œà²·à³€à²Ÿà³â€Œ à²—à²¡à³à²µà³" : "Chargesheet deadline"}\n            <span>{kn ? "à²¤à²¨à²¿à²–à³†à²¯à²²à³à²²à²¿à²°à³à²µ à²ªà³à²°à²•à²°à²£à²—à²³à³ A· BNSS A 187(3)" : "open investigations A· BNSS s.187(3)"}</span>\n          </div>',
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}>\n            {kn ? "à²šà²¾à²°à³à²œà³â€Œà²·à³€à²Ÿà³â€Œ à²—à²¡à³à²µà³" : "Chargesheet deadline"}\n            <span>{kn ? "à²¤à²¨à²¿à²–à³†à²¯à²²à³à²²à²¿à²°à³à²µ à²ªà³à²°à²•à²°à²£à²—à²³à³ A· BNSS A 187(3)" : "open investigations A· BNSS s.187(3)"}</span>\n          </summary>'
)

content = content.replace(
    '<div className="ov-panel ov-outcomes">',
    '<details className="ov-panel ov-outcomes">'
)

content = content.replace(
    '<div className="ov-ptitle">\n            {kn ? "à²ªà³à²°à²•à²°à²£à²¦ à²«à²²à²¿à²¤à²¾à²‚à²¶à²—à²³à³" : "Case outcomes"}\n            <span>{kn ? "100 FIR à²—à²³à²¿à²—à³†" : "rates per 100 FIRs"}</span>\n          </div>',
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}>\n            {kn ? "à²ªà³à²°à²•à²°à²£à²¦ à²«à²²à²¿à²¤à²¾à²‚à²¶à²—à²³à³" : "Case outcomes"}\n            <span>{kn ? "100 FIR à²—à²³à²¿à²—à³†" : "rates per 100 FIRs"}</span>\n          </summary>'
)

# And replace the closing </div> of ov-panel with </details>
# This is a bit tricky with regex, so let's do a more robust script
