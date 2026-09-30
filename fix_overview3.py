import sys

filepath = r"D:\Project\antar-frontend\components\DataOverview.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}> {kn ? "ವರ್ಗವಾರು ಹಂಚಿಕೆ" : "By crime category"} <span>{kn ? "ಕ್ಲಿಕ್ = ಫಿಲ್ಟರ್" : "click to filter"}</span></div>',
    '<div className="ov-ptitle"> {kn ? "ವರ್ಗವಾರು ಹಂಚಿಕೆ" : "By crime category"} <span>{kn ? "ಕ್ಲಿಕ್ = ಫಿಲ್ಟರ್" : "click to filter"}</span></div>'
)
content = content.replace(
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}> {kn ? "ತಿಂಗಳ ಟ್ರೆಂಡ್ \u00b7 ಕಳೆದ 24 ತಿಂಗಳು" : "Monthly trend \u00b7 last 24 months"}',
    '<div className="ov-ptitle"> {kn ? "ತಿಂಗಳ ಟ್ರೆಂಡ್ \u00b7 ಕಳೆದ 24 ತಿಂಗಳು" : "Monthly trend \u00b7 last 24 months"}'
)
content = content.replace(
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}> {kn ? "ತನಿಖೆಯ ಹಂತ" : "Investigation stage"} <span>{kn ? "ಕ್ಲಿಕ್ = ಫಿಲ್ಟರ್" : "click to filter"}</span></div>',
    '<div className="ov-ptitle"> {kn ? "ತನಿಖೆಯ ಹಂತ" : "Investigation stage"} <span>{kn ? "ಕ್ಲಿಕ್ = ಫಿಲ್ಟರ್" : "click to filter"}</span></div>'
)
content = content.replace(
    '<summary className="ov-ptitle" style={{cursor: "pointer"}}> {kn ? "ಜಿಲ್ಲೆಗಳ ಹಂಚಿಕೆ" : "District distribution"} <span>{kn ? "ಕ್ಲಿಕ್ = ಫಿಲ್ಟರ್" : "click to filter"}</span></div>',
    '<div className="ov-ptitle"> {kn ? "ಜಿಲ್ಲೆಗಳ ಹಂಚಿಕೆ" : "District distribution"} <span>{kn ? "ಕ್ಲಿಕ್ = ಫಿಲ್ಟರ್" : "click to filter"}</span></div>'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed DataOverview.jsx")
