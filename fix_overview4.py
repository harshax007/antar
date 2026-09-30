import sys

filepath = r"D:\Project\antar-frontend\components\DataOverview.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    '<div className="ov-ptitle">\n          {kn ? "ದೋಷಾರೋಪ ಗಡುವು" : "Chargesheet deadline"}\n          <span>{kn ? "ತನಿಖೆಯಲ್ಲಿರುವ ಪ್ರಕರಣಗಳು · BNSS §187(3)" : "open investigations · BNSS s.187(3)"}</span>\n         </summary>',
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}>\n          {kn ? "ದೋಷಾರೋಪ ಗಡುವು" : "Chargesheet deadline"}\n          <span>{kn ? "ತನಿಖೆಯಲ್ಲಿರುವ ಪ್ರಕರಣಗಳು · BNSS §187(3)" : "open investigations · BNSS s.187(3)"}</span>\n         </summary>'
)

content = content.replace(
    '<div className="ov-ptitle">\n          {kn ? "ಪ್ರಕರಣದ ಫಲಿತಾಂಶಗಳು" : "Case outcomes"}\n          <span>{kn ? "100 FIR ಗಳಿಗೆ" : "rates per 100 FIRs"}</span>\n         </summary>',
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}>\n          {kn ? "ಪ್ರಕರಣದ ಫಲಿತಾಂಶಗಳು" : "Case outcomes"}\n          <span>{kn ? "100 FIR ಗಳಿಗೆ" : "rates per 100 FIRs"}</span>\n         </summary>'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed ov-ptitle")
