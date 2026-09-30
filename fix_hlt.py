import sys
import re

filepath = r"D:\Project\antar-frontend\app\(app)\antar\page.jsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add global counter
if "let GLOBAL_HL_COUNT = 0;" not in content:
    content = content.replace("const HILITE_RE =", "let GLOBAL_HL_COUNT = 0;\nconst HILITE_RE =")

# 2. Reset counter at the start of MessageRow
if "GLOBAL_HL_COUNT = 0;" not in content:
    content = content.replace(
        "const MessageRow = memo(({",
        "const MessageRow = memo(({\n"
    )
    content = re.sub(
        r'(translateAnswer,\s*rateAnswer,\s*toggleWhy\s*}\)\s*=>\s*\{)',
        r'\1\n    GLOBAL_HL_COUNT = 0;',
        content
    )

# 3. Modify Highlighted component
highlight_old = """function Highlighted({ text }) {
    const parts = String(text || "").split(HILITE_RE);
    return parts.map((p, i) => {
      if (i % 2 === 1) {
        if (/^\d{4}$/.test(p)) {
          const prev = parts[i - 1] || "";
          if (/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+$/i.test(prev)) {
            return p;
          }
        }
        return <b key={i} className="cx-hl">{p}</b>;
      }
      return p;
    });
  }"""
  
highlight_new = """function Highlighted({ text }) {
    const parts = String(text || "").split(HILITE_RE);
    return parts.map((p, i) => {
      if (i % 2 === 1) {
        if (/^\d{4}$/.test(p)) {
          const prev = parts[i - 1] || "";
          if (/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+$/i.test(prev)) {
            return p;
          }
        }
        if (GLOBAL_HL_COUNT < 2) {
            GLOBAL_HL_COUNT++;
            return <b key={i} className="cx-hl">{p}</b>;
        }
        return p;
      }
      return p;
    });
  }"""
  
if "if (GLOBAL_HL_COUNT < 2) {" not in content:
    content = content.replace(highlight_old, highlight_new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated page.jsx for highlighting limit")
